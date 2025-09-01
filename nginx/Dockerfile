# NGINX Dockerfile

# Use the lightweight nginx:1.19.7-alpine base image
FROM nginx:1.19.7-alpine

# Install bash for boot command
RUN apk add bash

# Add nginx.conf and start.sh to the container with proper ownership
COPY --chown=nginx:nginx nginx.conf /etc/nginx/nginx.conf
COPY --chown=nginx:nginx start.sh /app/start.sh

# Set the working directory
WORKDIR /app

# Set permissions and nginx user for tightened security
RUN chown -R nginx:nginx /app && chmod -R 755 /app && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chmod -R 755 /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d

# Create the NGINX process ID file and set proper ownership
RUN touch /var/run/nginx.pid && chown -R nginx:nginx /var/run/nginx.pid

# Uncomment the following lines to keep the NGINX logs inside the container
# Leave commented for logging to stdout and stderr
# RUN mkdir -p /var/log/nginx
# RUN unlink /var/log/nginx/access.log \
#     && unlink /var/log/nginx/error.log \
#     && touch /var/log/nginx/access.log \
#     && touch /var/log/nginx/error.log \
#     && chown nginx /var/log/nginx/*log \
#     && chmod 644 /var/log/nginx/*log

# Run the container as the nginx user
USER nginx

# Start NGINX without daemonizing for proper container behavior
CMD ["nginx", "-g", "'daemon off;'"]
