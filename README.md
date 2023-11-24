# Small-Prox
A small local reverse proxy (such as nginx/haproxy) for handling many local docker containers.

This proxy routes traffic to specific containers based on host or path.
It also allows you to route traffic to local ports, in case you're not
using docker for some services (common for local dev).

All configuration is done via docker/docker-compose and you do not need a seperate config file.

This proxy is intended to route traffic to specific services much like the
load balancer would on a real environment (production). It helps develop locally.

**Note: This proxy/project is intended to ease local development. There is no
security/performance considerations made at all. I do not recommend using this
to route traffic anywhere except locally.**

# How does it work?
The container listens on the docker socket and watches for containers to start up.
The containers have a label that specifies what host and path they want
to handle traffic for, and this proxy sends it to them on those conditions.

For local forwarding, the container finds the host ip address and forwards there. For Docker on Mac (or windows), this is a dns address, but for linux its in the containers ip tables.

# Getting started

To run the container simply use:

```bash
docker run -d -p 80:80 -v /var/run/docker.sock:/var/run/docker.sock nhumrich/small-prox
```

or use docker-compose compose.yaml file:
```yaml
services:
  smallprox:
    image: nhumrich/small-prox
    ports:
      - "80:80"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```

## Real World Example:
Let's say you have a frontend site running at `localhost:3000` and a backend site running at `localhost:8080`. Don't forget to also add `127.0.0.1 mysite.local` to your /etc/hosts file.
```yaml
services:
  smallprox:
    image: nhumrich/small-prox
    ports:
      - "80:80"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      LOCAL_PORTS: "mysite.local=3000,mysite.local/api=8080"
```

### Forwarding to docker containers
Start your container with a label:

```bash
docker run -l proxy_expose=myapp.myhost.local=8080 myorg/mycontainer
```

The format is:
`proxy_expose={host}/{path}={port container listens on}`

If you are doing host based networking, you will need to add the hosts in your
/etc/hosts file pointing to 127.0.0.1 or use an actual dns record that resolves
to 127.0.0.1

### Forwarding to local ports
If you would like to forward traffic to local ports, you can do this by setting
environment variables on the small-prox container before you start it.

The environment variable is `LOCAL_PORTS` and excepts a comma-separated list of 
strings in the format of `{host}/{path}={port}`.


## Full list of config options

### LOCAL_PORTS

You can send traffic to things running locally using the `LOCAL_PORTS` environment variable on the small-prox container.
This is a comma-seperated string. This setting always takes priority over any other settings.
If you have containers mapped to specific hosts or paths, the local_port always wins.

Some examples:

`LOCAL_PORTS: "mysite.local=3000,mysite.local/api=8080"` This Routes all traffic to mysite.local to 
port 3000 locally. It also routes traffic starting with `/api` to port 8080 instead.

`LOCAL_PORTS: "/=8000,/api=8080,/static=3000` This routes all traffic on _any host_ including localhost to port 8000.
If the path starts with `api` it will go to port 8080 instead, and likewise, all paths starting with static will go to 3000

`LOCAL_PORTS: "/api=8080,mysite.local/api=8181` This will route all traffic on _any host_ including localhost to port 8080 as 
log as it starts with the `api` path prefix. However, if the host is specifically `mysite.local` it will go to port 8181 instead.

### LOCAL_ADDRESS

When running on Docker for Mac/Windows, docker adds some dns to allow this container to talk to the host.
Sometimes, that address is wrong (Typically when running docker inside WSL2 without using Docker for Windows)

This environment variable allows one to override the typical resolution IP address for "local" and use this instead.
If you have connection issues for `LOCAL_PORTS`, you could play around with this. 
If you are using docker-compose, you could potentially add your own override.yaml file so that the setting applies only to you:

```yaml
services:
    proxy:
        environment:
            LOCAL_ADDRESS: '172.21.0.1'
```

### REMOTE_PORTS:

This environment variable is very similar to `LOCAL_PORTS` except that it sends traffic to anywhere, even potentially a remote address.
The proxy will rewrite the host header so that the receiving server does not know the original host used.
Typically, this is needed when you want something like `service.local` to point to a remote service `myservice.example.com`.
It is a great feature for taking local-dependencies and moving them to the cloud.
For `LOCAL_PORTS` the right side of the `=` is a port, but for REMOTE_PORTS its a fully qualified url.

Examples:

`REMOTE_PORTS: "/api=staging.example.com,myservice.local=123.123.123.123:8181`

### DEBUG

Setting `DEBUG=true` will make the proxy give you debug logs. Useful for debugging networking issues.
It should tell you what all the registered host-port mappings are, and also print out all incoming requests, and where it wants to send them.

### NO_HTTPS_REDIRECT

If you are using ssl certificates, then the proxy will automatically redirect any http calls to https.
If you would like to disable the https redirect, you can set this: `NO_HTTPS_REDIRECT=true`, which disables it.

### Container Ports

This is not configurable via environment variables, but instead via labels. You can have small-prox
send traffic to a specific container by adding a label to that container. Small prox reads docker labels
to know which containers to send traffic too.

An example for docker compose:
```yaml
services:
  backend:
    image: myorg/myimage
    labels:
      proxy_expose: local.example.com/api=8008

```  
This will route all traffic from local.example.com that is prefixed with the `api` path, to this container on port 8008.

### Intercept docker traffic

Small-prox is great for intercepting local traffic, such as local-host, and sending it wherever. (a container, a local service, etc.)
But its also useful for sending traffic that originates from a container! In order to do that, you need to tell docker to intercept 
traffic for the host.
You can do that by adding network aliases. 

A full example in docker-compose:
```yaml
services:
  smallprox:
    image: nhumrich/small-prox
    ports:
      - "80:80"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      LOCAL_PORTS: "mysite.local=3000,mysite.local/api=8080"
    networks:
      default:
        aliases:
         - mysite.local
```

Now another container will go to small-prox when it calls `mysite.local`, which will then in turn end up in your local container.

# FAQ
 
### Can I use this in prod?
I mean, you *could*, but I dont recommend it.

### Does it support ssl?
Sure does! You just need to port forward port 443 as well, and also drop a `fullchain.pem` and `privkey.pem` file into
the `/certs/` directory in the container and ssl will work. You could either volume mount these in
or build your own container on top of this one. The file names are the names letsencrypt uses. 
 You could use self-signed certs, or you could create a DNS name that points to 127.0.0.1 and use dns
 validation to get a lets encrypt cert for your local dev.
 
### Why did you build this? Why not just use jwilder/nginx-proxy (or similar)?
There are a couple reasons. `jwilder/nginx-proxy` is excellent but it only does
 host routing. I wanted path based routing as well. Also, I wanted to be able to
 route to local ports, for when i'm debugging locally and dont want to run my service inside a container.
 
Another possibility is just use nginx by itself. This works great until you want to change things, such
as where a service is or what path/port it listens to. I was using a custom nginx image at my
organization, but ended up having many many versions of it for all the different configurations
people wanted. I found that I wanted the "configuration" outside of the container, and 
in the persons repo. So, here is something a little more dynamic, and loads configuration from other places 
(docker labels). Plus, now that its in python, it gives me more flexibility to add things in the future
if I want.z

### Does this use nginx/similar under the hood?
No. This project is written entirely in python. I had thought of just implementing it by
looking for docker changes, updating the nginx configuration and restarting nginx.
The amount of work (not much) to do that, is about the same to just listen to http and 
forward packets. I decided to do it entirely in python as a learning experience for myself.
Since the project is intended for local development only, I am not concerned about
security/performance issues. 
That being said, this project uses asyncio and one of python's fastest http parsers, so you
shouldn't notice any slowness from it. 

