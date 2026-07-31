FROM node:20-slim AS build
WORKDIR /build
ENV npm_config_registry=https://registry.npmmirror.com
COPY widget ./widget
COPY agent-console ./agent-console
RUN cd widget && npm install && npm run build
RUN cd agent-console && npm install && npm run build

FROM nginx:1.27
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /build/widget/dist /usr/share/nginx/html/widget
COPY --from=build /build/agent-console/dist /usr/share/nginx/html/console
