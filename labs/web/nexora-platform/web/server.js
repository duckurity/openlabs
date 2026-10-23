import express from 'express';
import cors from 'cors';
import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';
import sqlite3 from 'sqlite3';
import { promisify } from 'util';
import { Resolver } from 'dns/promises';
import http from 'http';
import https from 'https';
import { ApolloServer } from '@apollo/server';
import { expressMiddleware } from '@apollo/server/express4';

const app=express(), db=new sqlite3.Database('/app/nexora.db');
const run=promisify(db.run.bind(db)), get=promisify(db.get.bind(db)), all=promisify(db.all.bind(db));
const JWT_SECRET='nexora-staging-signing-key'; const resolver=new Resolver(); resolver.setServers(['172.28.0.53']);
const completionValue=()=>String.fromCharCode(100,117,99,107,123,83,83,82,70,95,105,110,95,71,114,97,112,104,81,76,125);
await run('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT, company TEXT, email TEXT UNIQUE, password TEXT)');
await run('CREATE TABLE IF NOT EXISTS integrations(id INTEGER PRIMARY KEY, name TEXT, endpoint TEXT, type TEXT, user_id INTEGER)');
const tokenFor=u=>jwt.sign({id:u.id,email:u.email,name:u.name},JWT_SECRET,{expiresIn:'8h'});
function user(req){try{return jwt.verify((req.headers.authorization||'').replace('Bearer ',''),JWT_SECRET)}catch{return null}}
function requireUser(req,res,next){const u=user(req); if(!u)return res.status(401).json({error:'Authentication required'});req.user=u;next()}
function privateIp(ip){return /^127\.|^10\.|^192\.168\.|^172\.(1[6-9]|2\d|3[01])\.|^169\.254\.|^0\./.test(ip)||ip==='::1'}
async function resolve(host){return (await resolver.resolve4(host))[0]}
function requestUrl(raw){return new Promise(async(resolveResult)=>{let url;try{url=new URL(raw)}catch{return resolveResult({reachable:false})} if(!['http:','https:'].includes(url.protocol))return resolveResult({reachable:false});
  let validated;try{validated=await resolve(url.hostname)}catch{return resolveResult({reachable:false})}; if(privateIp(validated))return resolveResult({reachable:false});
  let connectedIp='';const agent=url.protocol==='https:'?https:http; const req=agent.request(url,{timeout:3500,lookup:(host,opts,cb)=>{if(typeof opts==='function'){cb=opts;opts={}}resolve(host).then(ip=>{connectedIp=ip;opts.all?cb(null,[{address:ip,family:4}]):cb(null,ip,4)}).catch(cb)}},res=>{res.resume();const result={reachable:true};Object.defineProperty(result,'metadataReached',{value:connectedIp==='172.28.0.10',enumerable:false});resolveResult(result)});req.on('timeout',()=>{req.destroy();resolveResult({reachable:false})});req.on('error',()=>resolveResult({reachable:false}));req.end();
 })}
app.use(express.json());app.use(express.static('public'));
app.get('/api/v1/health',(q,s)=>s.json({status:'ok',service:'nexora-web'})); app.get('/api/v1/status',(q,s)=>s.json({status:'operational',region:'us-central1'}));
app.post('/api/v1/auth/register',async(req,res)=>{const {name,company,email,password}=req.body;if(!name||!company||!email||!password)return res.status(400).json({error:'All fields are required'});try{await run('INSERT INTO users(name,company,email,password) VALUES(?,?,?,?)',[name,company,email,await bcrypt.hash(password,10)]);res.status(201).json({message:'Account created successfully. Please sign in to continue.'})}catch{res.status(409).json({error:'Email already registered'})}});
app.post('/api/v1/auth/login',async(req,res)=>{const u=await get('SELECT * FROM users WHERE email=?',[req.body.email]);if(!u||!await bcrypt.compare(req.body.password||'',u.password))return res.status(401).json({error:'Invalid email or password'});res.json({token:tokenFor(u),user:{name:u.name,email:u.email}})});
app.post('/api/v1/auth/logout',(q,s)=>s.status(204).end());app.get('/api/v1/auth/me',requireUser,(q,s)=>s.json(q.user));app.post('/api/v1/auth/forgot-password',(q,s)=>s.json({message:'If the account exists, reset instructions have been sent.'}));app.post('/api/v1/auth/reset-password',(q,s)=>s.status(400).json({error:'Reset token is invalid or expired'}));
app.get('/api/v1/integrations',requireUser,async(q,s)=>s.json(await all('SELECT id,name,endpoint,type FROM integrations WHERE user_id=?',[q.user.id])));app.post('/api/v1/integrations',requireUser,async(q,s)=>{const r=await run('INSERT INTO integrations(name,endpoint,type,user_id) VALUES(?,?,?,?)',[q.body.name,q.body.endpoint,q.body.type,q.user.id]);s.status(201).json({id:r.lastID})});
app.get('/api/v1/webhooks',requireUser,(q,s)=>s.json([]));app.get('/api/v1/activity',requireUser,(q,s)=>s.json([{event:'Workspace created',at:new Date().toISOString()}]));
app.post('/api/v1/validate',requireUser,async(q,s)=>s.json(await requestUrl(q.body.url)));app.post('/api/v1/preview',requireUser,async(q,s)=>s.json(await requestUrl(q.body.url)));app.post('/api/v1/webhooks',requireUser,async(q,s)=>s.json(await requestUrl(q.body.endpoint)));
const typeDefs=`type Reachability { reachable: Boolean!, flag: String } type User { id: ID!, name: String!, email: String! } type Integration { id: ID!, name:String!, endpoint:String!, type:String! } type Query { me: User, integrations: [Integration!]!, integration(id:ID!): Integration, activity:[String!]!, UrlReachable(url:String!): Reachability! } type Mutation { createIntegration(name:String!, endpoint:String!, type:String!): Integration!, testWebhook(url:String!): Reachability!, validateUrl(url:String!): Reachability! }`;
const resolvers={Query:{me:(_,__,c)=>c.user,integrations:async(_,__,c)=>c.user?await all('SELECT id,name,endpoint,type FROM integrations WHERE user_id=?',[c.user.id]):[],integration:async(_,{id},c)=>c.user?await get('SELECT id,name,endpoint,type FROM integrations WHERE id=? AND user_id=?',[id,c.user.id]):null,activity:()=>['Workspace initialized'],UrlReachable:async(_,{url})=>{const r=await requestUrl(url);return r.metadataReached?{...r,flag:completionValue()}:r}},Mutation:{createIntegration:async(_,{name,endpoint,type},c)=>{if(!c.user)throw new Error('Authentication required');const r=await run('INSERT INTO integrations(name,endpoint,type,user_id) VALUES(?,?,?,?)',[name,endpoint,type,c.user.id]);return{id:r.lastID,name,endpoint,type}},testWebhook:async(_,{url})=>requestUrl(url),validateUrl:async(_,{url})=>requestUrl(url)}};
const apollo=new ApolloServer({typeDefs,resolvers,introspection:true});await apollo.start();app.use('/graphql',cors(),expressMiddleware(apollo,{context:async({req})=>({user:user(req)})}));
for(const p of ['/','/login','/register','/dashboard','/integrations','/integrations/','/webhooks','/activity','/developers','/docs','/settings'])app.get(p,(q,s)=>s.sendFile('/app/public/index.html'));
app.listen(8080,'0.0.0.0');
