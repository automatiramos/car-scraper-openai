# 🚗 Car Scraper OpenAI

**Scrape it. Rate it. Own it.**  
An automated workflow that collects vehicle data from a configurable listing URL, evaluates the features with OpenAI, and stores everything in clean JSON files.  
Runs daily with GitHub Actions — no manual clicks, just fresh data.

---

## 📦 What it does

1. **Data extraction** → Uses Playwright to scrape a public listing page (`scrapping_cars.py`).
2. **Smart evaluation** → Sends each vehicle's equipment description to OpenAI for rating (`ask_openai_car_evaluation.py`).
3. **Storage** → Saves results as JSON (individual per car + daily merged file).

---

## 🛠 Requirements

- Python 3.11+
- OpenAI API key
- Playwright Chromium installed
- GitHub Actions (for automation)

---

## ⚙️ Local Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/your-user/car-scraper-openai.git
   cd car-scraper-openai
   ```
