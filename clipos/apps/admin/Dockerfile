FROM node:20-alpine AS base
WORKDIR /app
COPY package.json ./
RUN npm install --frozen-lockfile 2>/dev/null || npm install
COPY . .
RUN npm run build
EXPOSE 3001
CMD ["npm", "start"]
