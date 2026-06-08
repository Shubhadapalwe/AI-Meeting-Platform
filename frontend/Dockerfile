FROM node:22-alpine
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
# certs/ is mounted at runtime via docker-compose volumes
CMD ["npm", "run", "dev"]
