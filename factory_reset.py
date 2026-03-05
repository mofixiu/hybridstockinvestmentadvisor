import subprocess
import sys
import time

def run_command(command, description):
    """Runs a terminal command and handles errors."""
    print(f"\n{'='*50}")
    print(f"🚀 STEP: {description}")
    print(f"💻 Executing: {command}")
    print(f"{'='*50}\n")
    
    try:
        # Run the command and wait for it to finish
        result = subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ ERROR: The pipeline failed at: {description}")
        print("Please check the logs above to fix the issue before restarting.")
        sys.exit(1)

def main():
    print("\n⚠️  INITIATING TOTAL SYSTEM FACTORY RESET ⚠️")
    print("This will rebuild the AI models, fetch fresh data, and restart the API.")
    time.sleep(2) # Give the user a second to cancel if they didn't mean to run this

    # Step 1: Rebuild the Technical AI
    run_command(
        "python3 src/modeltraining/train_optimized.py", 
        "Training LightGBM Technical Model"
    )

    # Step 2: Rebuild the NLP AI
    run_command(
        "python3 src/modeltraining/train_nlp.py", 
        "Training Naija-FinBERT NLP Engine"
    )

    # Step 3: Run the Daily Data Pipeline
    run_command(
        "python3 src/data/daily_update.py", 
        "Executing Multi-Modal Data Fetch & Scoring"
    )

    # Step 4: Start the Server (This blocks the terminal to keep the server alive)
    print(f"\n{'='*50}")
    print("🟢 ALL SYSTEMS GO. STARTING THE FASTAPI SERVER...")
    print(f"{'='*50}\n")
    
    try:
        subprocess.run("uvicorn src.api.main:app --reload", shell=True, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server manually stopped. Reset complete.")

if __name__ == "__main__":
    main()