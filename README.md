# Small-Prox
A small local reverse proxy (such as nginx/haproxy) for handling many local docker containers.

This proxy routes traffic to specific containers based on host or path.
It also allows you to route traffic to local ports, in case your not
using docker for some services (common for local dev).

This proxy is intended to route traffic to specific services much like the
load balancer would on a real environment (production). It helps develop locally.
 
**Note: This proxy/project is intended to ease local development. There is no
security/performance considerations made at all. I do not recommend using this
to route traffic anywhere except locally.**

# How does it work?
The container listens on the docker socket and watches for containers to start up.
The containers have a label that specifies what host and path they want
to handle traffic for, and this proxy sends it to them on those conditions.

# Getting started

To run the container simply use:

```bash
docker run -d --net host -v /var/run/docker.sock:/var/run/docker.sock nhumrich/small-prox
```

or use docker-compose:
```yaml
version: '3'
services:
  smallprox:
    image: nhumrich/small-prox
        network_mode: host
        volumes:
          - /var/run/docker.sock:/var/run/docker.sock
```

### Forwarding to docker containers
Start your container with a label

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


# FAQ

### Do I need to use host networking (`--net host`)?

Depends on how your using this. If you are only using this proxy to proxy to containers,
 then you could just forward port 80 and 443. However, in order to use the 
 "local port forwarding" feature, you will need to run on the host network.
 
### Can I use this in prod?
I mean, you *could*, but I dont recommend it.

### Does it support ssl?
Sure does! You just need to drop a `fullchain.pem` and `privkey.pem` file into
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
if I want.

### Does this use nginx/similar under the hood?
No. This project is written entirely in python. I had thought of just implementing it by
looking for docker changes, updating the nginx configuration and restarting nginx.
The amount of work (not much) to do that, is about the same to just listen to http and 
forward packets. I decided to do it entirely in python as a learning experience for myself.
Since the project is intended for local development only, I am not concerned about
security/performance issues. 
That being said, this project uses asyncio and one of pythons fastest http parsers, so you
shouldn't notice any slowness from it. 

