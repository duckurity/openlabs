defmodule TenantExchangeWeb.Router do
  use TenantExchangeWeb, :router

  pipeline :browser do
    plug :accepts, ["html"]
    plug :fetch_session
    plug :protect_from_forgery
    plug :put_secure_browser_headers
  end

  pipeline :api do
    plug :accepts, ["json"]
    plug :fetch_session
  end

  scope "/", TenantExchangeWeb do
    pipe_through :browser

    get "/", PageController, :home
    get "/login", PageController, :login
    get "/register", PageController, :register
    get "/otp", PageController, :otp
    post "/register", SessionController, :register
    post "/login", SessionController, :create
    post "/otp", SessionController, :verify_otp
    post "/logout", SessionController, :delete
    get "/inbox", PageController, :inbox
    get "/notifications", PageController, :inbox
    get "/exchange/lookup", PageController, :exchange_lookup
    match :*, "/*path", PageController, :not_found
  end

end
