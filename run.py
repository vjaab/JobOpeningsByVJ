import logging
import argparse
from src.main import main, run_job_scraping
from src.utils.db import init_db
from src.agents.interview_agent import InterviewPrepAgent

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Job Openings Scraper Service")
    parser.add_argument('--run-once', action='store_true', help="Run the scraper once and exit")
    parser.add_argument('--run-agent-once', action='store_true', help="Run the interview prep agent once and exit")
    args = parser.parse_args()

    # Ensure DB is initialized
    init_db()

    try:
        if args.run_once:
            run_job_scraping()
        elif args.run_agent_once:
            logging.info("Starting standalone Interview Prep Agent run...")
            agent = InterviewPrepAgent()
            agent.execute_daily_run()
        else:
            main()
    except KeyboardInterrupt:
        logging.info("Service stopped by user")
    except Exception as e:
        logging.critical(f"Service crashed: {e}", exc_info=True)

