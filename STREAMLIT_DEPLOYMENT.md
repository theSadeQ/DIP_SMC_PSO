# Streamlit Deployment Guide

This guide covers deploying the DIP_SMC_PSO Streamlit application locally and on cloud platforms.

## Quick Start

### Local Development
```bash
# Install Streamlit-specific dependencies
pip install -r requirements-streamlit.txt

# Run the app locally
streamlit run streamlit_app.py

# Access at http://localhost:8501
```

### Performance Features

The app includes several performance optimizations:

- **Caching**: Expensive operations (simulation, PSO optimization) are cached using `@st.cache_data`
- **Configuration Caching**: Config loading is cached to avoid repeated file I/O
- **Lazy Loading**: Visualization components load only when needed

## Deployment Options

### 1. Streamlit Cloud (Recommended)

1. **Fork the repository** on GitHub
2. **Connect to Streamlit Cloud**:
   - Visit [share.streamlit.io](https://share.streamlit.io)
   - Sign in with GitHub
   - Click "New app"
   - Select this repository
   - Set main file: `streamlit_app.py`
   - Set Python version: 3.9+

3. **Environment Variables** (if needed):
   ```
   PYTHONPATH=./src
   ```

4. **Configuration**:
   - Uses `.streamlit/config.toml` for app settings
   - Custom theme with DIP_SMC_PSO branding
   - Optimized for performance and security

### 2. Docker Deployment

Create a `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements-streamlit.txt .
RUN pip install --no-cache-dir -r requirements-streamlit.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run app
ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Build and run:
```bash
docker build -t dip-smc-pso-app .
docker run -p 8501:8501 dip-smc-pso-app
```

### 3. Heroku Deployment

1. **Create required files**:

`Procfile`:
```
web: sh setup.sh && streamlit run streamlit_app.py --server.port=$PORT --server.address=0.0.0.0
```

`setup.sh`:
```bash
#!/bin/bash
mkdir -p ~/.streamlit/
echo "\
[general]\n\
email = \"your-email@domain.com\"\n\
" > ~/.streamlit/credentials.toml
echo "\
[server]\n\
headless = true\n\
enableCORS=false\n\
port = $PORT\n\
" > ~/.streamlit/config.toml
```

2. **Deploy**:
```bash
git add .
git commit -m "Deploy to Heroku"
heroku create your-app-name
git push heroku main
```

### 4. AWS EC2 / VPS Deployment

```bash
# Install dependencies
sudo apt update
sudo apt install python3-pip nginx

# Clone repository
git clone <your-repo-url>
cd DIP_SMC_PSO

# Install Python dependencies
pip3 install -r requirements-streamlit.txt

# Run with systemd service
sudo tee /etc/systemd/system/dip-smc-pso.service > /dev/null <<EOF
[Unit]
Description=DIP SMC PSO Streamlit App
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/DIP_SMC_PSO
Environment=PATH=/home/ubuntu/.local/bin
ExecStart=/home/ubuntu/.local/bin/streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Start service
sudo systemctl daemon-reload
sudo systemctl enable dip-smc-pso
sudo systemctl start dip-smc-pso
```

## Configuration Details

### Theme Customization

The app uses a custom theme defined in `.streamlit/config.toml`:

- **Primary Color**: `#FF6B6B` (vibrant red for buttons and accents)
- **Background**: Clean white with subtle gray secondary backgrounds
- **Typography**: Dark text for optimal readability

### Performance Settings

- **Magic Mode**: Enabled for automatic rerun detection
- **Matplotlib Fix**: Prevents figure accumulation
- **Upload Limit**: 100MB for large datasets
- **XSRF Protection**: Enabled for security

### Security Considerations

- **CORS**: Disabled for production
- **Error Details**: Hidden from users in production
- **Usage Stats**: Disabled for privacy
- **Development Mode**: Disabled for production

## Monitoring and Maintenance

### Health Checks

The app includes built-in health monitoring:

```python
# Add to streamlit_app.py for custom health endpoint
import streamlit as st

if st.sidebar.button("Health Check"):
    st.success("✅ Application is running normally")
    st.info(f"Cache size: {len(st.session_state)} items")
```

### Performance Monitoring

- **Cache Hit Rates**: Monitor via Streamlit's built-in cache metrics
- **Memory Usage**: Watch for cache size growth
- **Response Times**: Monitor simulation and PSO execution times

### Troubleshooting

**Common Issues:**

1. **Import Errors**: Ensure `PYTHONPATH` includes `./src`
2. **Memory Issues**: Clear cache periodically with `st.cache_data.clear()`
3. **Slow Performance**: Check cache configuration and data sizes
4. **Port Conflicts**: Use environment variable `PORT` for dynamic ports

**Debug Mode:**
```bash
streamlit run streamlit_app.py --logger.level=debug
```

## Features Overview

### Interactive Controls
- Real-time parameter tuning for all controller types
- Initial condition customization
- Disturbance injection capabilities
- Animation controls and export options

### Visualization Exports
- High-resolution PNG plots (150 DPI)
- Simulation data in JSON format
- Complete results in downloadable ZIP files
- Phase space plots and time series analysis

### Performance Features
- Intelligent caching for expensive operations
- Progress bars for long-running PSO optimizations
- Responsive UI with immediate parameter feedback
- Memory-efficient animation handling

This deployment guide ensures your DIP_SMC_PSO Streamlit application runs reliably across different platforms with optimal performance and security.