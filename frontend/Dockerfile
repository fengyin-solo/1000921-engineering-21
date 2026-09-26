FROM node:20-alpine
WORKDIR /srv/web
# 先拷贝锁文件，严格按 package-lock.json 安装可复现依赖
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
