import express from 'express';
const app=express(), interactions=[];app.use(express.json());
function add(kind,data){interactions.unshift({kind,time:new Date().toISOString(),...data});interactions.splice(200)}
app.post('/api/dns',(q,s)=>{add('DNS',{hostname:q.body.hostname});s.sendStatus(204)});
app.get('/api/interactions',(q,s)=>s.json(interactions));
app.get('/',(q,s)=>s.sendFile('/app/index.html'));
app.get('*',(q,s)=>{add('HTTP',{hostname:q.headers.host||'',path:q.originalUrl,headers:{'user-agent':q.headers['user-agent']||'',host:q.headers.host||''}});s.type('html').send('<h1>Local OAST</h1><p>Interaction received.</p>')});
app.listen(80,'0.0.0.0');
