import sys, os
sys.path.insert(0, '.')
from app.services.shot_detection_service import ShotDetectionService
from app.ai.shot_providers import collect_frames

# Create service
svc = ShotDetectionService()

# Test with threshold out of range
try:
    svc2 = ShotDetectionService(threshold=1.5)
    print('ERROR: should have raised')
except ValueError as e:
    print(f'OK: threshold error: {e}')

# Test with max_shots out of range
try:
    svc3 = ShotDetectionService(max_shots=200)
    print('ERROR: should have raised')
except ValueError as e:
    print(f'OK: max_shots error: {e}')

print('basic smoke tests passed')