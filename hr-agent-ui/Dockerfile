FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
ARG VITE_API_BASE_URL=
ARG VITE_MODEL_NAME=hr-agent
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_MODEL_NAME=${VITE_MODEL_NAME}
RUN npm run build

FROM nginx:1.27-alpine

COPY docker/nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
