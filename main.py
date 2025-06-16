
# main.py

import asyncio
import sys
import traceback

import config
import browser_scraper
import data_processor
import data_saver

async def run_automated_process():
    print("Starting automated order recommendation process...")
    config_data = None
    raw_data = None
    processed_data = None

    try:
        print("Loading configuration...")
        config_data = config.load_config()
        print("Configuration loaded successfully.")

        print("Initiating data scraping...")
        raw_data = await browser_scraper.scrape_data(config_data)
        print("Data scraping completed.")

        if not raw_data:
             print("Scraping returned no data. Aborting processing and saving steps.")
             return

        print("Processing scraped data...")
        processed_data = data_processor.process_data(raw_data)
        print("Data processing completed.")

        if processed_data is None:
             print("Data processing failed or returned empty result. Aborting saving step.")
             return

        print("Saving processed data...")
        data_saver.save_data(processed_data, config_data)
        print("Data saved successfully.")

    except Exception as e:
        print(f"An error occurred during the automated process: {e}", file=sys.stderr)
        print("Automated process failed due to an error.")

    finally:
        print("Automated process finished execution attempt.")

if __name__ == "__main__":
    try:
        asyncio.run(run_automated_process())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
    except Exception as e:
        print(f"An unhandled exception occurred during asyncio execution: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
