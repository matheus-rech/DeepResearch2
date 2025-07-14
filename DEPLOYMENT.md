# DeepResearch2 Deployment Guide

## Production Deployment

### Prerequisites

1. **Python Environment**
   ```bash
   python3.8+ with pip
   ```

2. **Database Setup (Optional)**
   ```bash
   # For PostgreSQL with vector support
   sudo apt-get install postgresql postgresql-contrib
   sudo -u postgres createdb deepresearch
   sudo -u postgres psql -c "CREATE EXTENSION vector;"
   ```

3. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your production values
   ```

### Installation

1. **Clone Repository**
   ```bash
   git clone https://github.com/matheus-rech/DeepResearch2.git
   cd DeepResearch2
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize Database**
   ```bash
   python -c "from sr_screener.database import init_db; init_db()"
   ```

### Running Services

#### Vector Store Mode (Default)
```bash
python main.py
```
- MCP Server: `http://localhost:8001/sse/`
- Health Check: `http://localhost:8001/health`

#### Systematic Review Mode
```bash
python main.py sr
```
- MCP Server: `http://localhost:8001/sse/`
- Health Check: `http://localhost:8001/health`

#### Both Modes (Recommended)
```bash
python sr_screener/main.py both
```
- MCP Server: `http://localhost:8001/sse/`
- Streamlit UI: `http://localhost:8000`
- Health Check: `http://localhost:8001/health`

### Process Management

#### Using systemd

1. **Create service file**
   ```bash
   sudo nano /etc/systemd/system/deepresearch.service
   ```

2. **Service configuration**
   ```ini
   [Unit]
   Description=DeepResearch2 MCP Server
   After=network.target

   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/path/to/DeepResearch2
   Environment=PATH=/path/to/DeepResearch2/.venv/bin
   ExecStart=/path/to/DeepResearch2/.venv/bin/python sr_screener/main.py both
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and start**
   ```bash
   sudo systemctl enable deepresearch
   sudo systemctl start deepresearch
   sudo systemctl status deepresearch
   ```

#### Using PM2

```bash
npm install -g pm2
pm2 start sr_screener/main.py --name deepresearch --interpreter python3 -- both
pm2 save
pm2 startup
```

### Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /sse/ {
        proxy_pass http://localhost:8001/sse/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /health {
        proxy_pass http://localhost:8001/health;
    }

    location / {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### SSL/TLS Configuration

```bash
# Using Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Monitoring

#### Health Checks
```bash
# Basic health check
curl http://localhost:8001/health

# MCP endpoint check
curl http://localhost:8001/sse/
```

#### Logging
```bash
# View systemd logs
sudo journalctl -u deepresearch -f

# View PM2 logs
pm2 logs deepresearch
```

### Security Considerations

1. **API Key Management**
   - Store API keys in environment variables
   - Use different keys for development and production
   - Rotate keys regularly

2. **Database Security**
   - Use strong passwords
   - Enable SSL connections
   - Restrict network access

3. **Network Security**
   - Use HTTPS in production
   - Configure firewall rules
   - Consider VPN for internal access

### Scaling

#### Horizontal Scaling
```bash
# Multiple instances with load balancer
pm2 start sr_screener/main.py --name deepresearch-1 --interpreter python3 -- both
pm2 start sr_screener/main.py --name deepresearch-2 --interpreter python3 -- both
```

#### Database Scaling
- Use PostgreSQL with read replicas
- Consider connection pooling
- Monitor query performance

### Troubleshooting

#### Common Issues

1. **Port conflicts**
   ```bash
   sudo netstat -tulpn | grep :8001
   sudo netstat -tulpn | grep :8000
   ```

2. **Database connection issues**
   ```bash
   python -c "from sr_screener.database import engine; print(engine.url)"
   ```

3. **API key issues**
   ```bash
   python -c "import os; print('OPENAI_API_KEY' in os.environ)"
   ```

#### Performance Monitoring
```bash
# System resources
htop
df -h
free -h

# Application metrics
curl http://localhost:8001/health | jq
```

### Backup and Recovery

#### Database Backup
```bash
# PostgreSQL
pg_dump deepresearch > backup.sql

# SQLite
cp citations.db backup_citations.db
```

#### Configuration Backup
```bash
cp .env .env.backup
tar -czf config_backup.tar.gz .env sr_screener/sample_criteria.json
```

### Updates and Maintenance

```bash
# Update code
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart services
sudo systemctl restart deepresearch
# or
pm2 restart deepresearch
```
