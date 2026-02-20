Rate limit 발생 시 어떤 수준의 대응을 원하시나요?

1. **Retry + UI (추천)** — adapter에서 rate limit 감지 + 재시도, Source 모델에 에러 상태, 프론트엔드에서 rate limit 표시
2. **Backend retry only** — adapter에서 rate limit 감지 및 재시도만. UI 변경 없음
3. **Detect + log only** — rate limit 구분 로깅만. 재시도 없이 다음 poll에서 재시도