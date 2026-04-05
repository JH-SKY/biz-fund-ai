"""채팅 도메인 예외 처리."""

from src.app.core.exceptions import (
    ForbiddenException, 
    NotFoundException, 
    ServiceUnavailableException, # 503 처리를 위해 필요
    RateLimitException           # 429 처리를 위해 필요
)

# 1. 404 Not Found: 상담방이 존재하지 않거나 논리 삭제된 경우
def chat_room_not_found() -> NotFoundException:
    return NotFoundException("요청하신 상담 내역을 찾을 수 없어요. 이미 종료되었거나 삭제된 상담일 수 있습니다.")

# 2. 403 Forbidden: 다른 사용자의 상담방에 접근하려는 경우
def chat_room_forbidden() -> ForbiddenException:
    return ForbiddenException("사장님의 사업장에서 진행한 상담이 아닙니다. 접근 권한이 없어요.")

# 3. 403 Forbidden: 닫힌 상담방에 메시지를 보내려는 경우
def chat_room_closed() -> ForbiddenException:
    return ForbiddenException("이미 종료된 상담입니다. 새로운 상담을 시작해주세요.")

# 4. 429 Too Many Requests: 단시간 내 과도한 요청 (명세 준수)
# 비유: "상담원이 현재 통화 중입니다. 잠시 후 다시 시도해 주세요."
def chat_rate_limit_exceeded() -> RateLimitException:
    return RateLimitException("짧은 시간 동안 너무 많은 질문을 하셨어요. 잠시 후 다시 이용해 주세요.")

# 5. 503 Service Unavailable: LLM 엔진 또는 AI 서버 장애 (명세 준수)
# 설계 의도: 외부 AI 서비스(OpenAI 등)의 일시적 장애를 클라이언트에게 명확히 전달
def ai_service_unavailable() -> ServiceUnavailableException:
    return ServiceUnavailableException("현재 비즈몽 AI가 잠시 쉬고 있어요. 잠시 후 다시 시도해 주시겠어요?")