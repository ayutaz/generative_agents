"""Background launcher for ReverieServer (non-interactive)."""
import sys
sys.path.insert(0, ".")

from reverie import ReverieServer

SIM_ORIGIN = "base_the_ville_isabella_maria_klaus"
SIM_NAME = "sim-feb18-morning"
STEPS = 3000

print(f"Starting ReverieServer: fork={SIM_ORIGIN}, sim={SIM_NAME}")
rs = ReverieServer(SIM_ORIGIN, SIM_NAME)
rs.server_sleep = 0  # バックグラウンド実行では待機不要
print(f"Personas: {list(rs.personas.keys())}")
print(f"=== READY ===")
print(f"Open http://localhost:8001/simulator_home NOW, then steps will begin.")
print(flush=True)
rs.start_server(STEPS)
rs.save()
print("Done. Simulation saved.")
