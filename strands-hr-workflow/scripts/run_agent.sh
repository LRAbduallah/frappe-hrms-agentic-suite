set -e

python3 -m alembic upgrade head
python3 app/agentic_workflow/leave_agent.py