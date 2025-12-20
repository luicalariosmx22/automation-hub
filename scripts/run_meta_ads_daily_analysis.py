"""
Script para ejecutar el job de anuncios Meta Ads con análisis y alertas.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Setup
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / 'src'))
load_dotenv(root_dir / '.env')

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Importar y ejecutar el job
from automation_hub.jobs.meta_ads_anuncios_daily import run

if __name__ == "__main__":
    run()
