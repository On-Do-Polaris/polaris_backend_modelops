"""
==================================================================
[모듈명] agents/distribution.py
배포 에이전트

[모듈 목표]
1) Slack으로 리포트 전송
2) 파일 업로드 지원
3) 봇이 초대된 모든 채널에 자동 배포 지원
==================================================================
"""
from typing import Dict, List
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from ..state import ESGTrendsState
from ..utils.config import Config
from ..utils.logging import get_logger

logger = get_logger("esg_agent.distribution")


def get_bot_channels(client: WebClient) -> List[str]:
    """봇이 멤버인 채널 목록 가져오기 (페이지네이션 포함)

    Args:
        client: Slack WebClient

    Returns:
        List[str]: 채널 ID 목록
    """
    channels = []
    try:
        # 페이지네이션으로 모든 채널 가져오기
        all_channels = []
        cursor = None

        while True:
            result = client.conversations_list(
                types="public_channel,private_channel",
                exclude_archived=True,
                limit=200,
                cursor=cursor
            )
            fetched_channels = result.get("channels", [])
            all_channels.extend(fetched_channels)

            cursor = result.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        logger.info(f"총 {len(all_channels)}개 채널 발견")

        for channel in all_channels:
            channel_name = channel.get('name', 'unknown')
            is_member = channel.get("is_member", False)
            logger.info(f"채널: #{channel_name} - is_member: {is_member}")

            if is_member:
                channels.append(channel["id"])
                logger.info(f"✅ 봇이 멤버인 채널: #{channel_name} ({channel['id']})")

        if not channels:
            logger.warning("봇이 멤버인 채널이 없습니다. '/invite @봇이름'으로 초대해주세요.")

    except SlackApiError as e:
        error_msg = e.response.get('error', 'unknown')
        logger.error(f"채널 목록 조회 실패: {error_msg}")
        if error_msg == "missing_scope":
            logger.error("필요한 권한: channels:read, groups:read")
        elif error_msg == "invalid_auth":
            logger.error("SLACK_BOT_TOKEN이 유효하지 않습니다")

    return channels


def distribute_report(state: ESGTrendsState) -> Dict:
    """리포트 배포 (Slack)

    Args:
        state: 현재 상태

    Returns:
        Dict: 업데이트할 상태 필드
    """
    logger.info("리포트 배포 시작")

    final_report = state.get("final_report", "")

    if not final_report:
        logger.warning("배포할 리포트가 없습니다")
        return {"errors": ["배포할 리포트가 없습니다"]}

    errors = []

    # Slack 배포
    if Config.SLACK_BOT_TOKEN:
        try:
            client = WebClient(token=Config.SLACK_BOT_TOKEN)

            # 채널 결정: "auto"면 봇이 초대된 모든 채널, 아니면 지정된 채널
            if Config.SLACK_CHANNEL.lower() == "auto":
                channels = get_bot_channels(client)
                if not channels:
                    logger.warning("봇이 초대된 채널이 없습니다")
                    return {"errors": ["봇이 초대된 채널이 없습니다"]}
                logger.info(f"자동 모드: {len(channels)}개 채널에 배포")
            else:
                channels = [Config.SLACK_CHANNEL]

            # 각 채널에 배포
            for channel in channels:
                try:
                    _send_to_channel(client, channel, final_report, state)
                    logger.info(f"채널 {channel} 배포 완료")
                except Exception as e:
                    error_msg = f"채널 {channel} 배포 실패: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

        except Exception as e:
            error_msg = f"Slack 배포 실패: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
    else:
        logger.warning("SLACK_BOT_TOKEN이 없어 배포를 건너뜁니다")

    return {"errors": errors} if errors else {}


def _send_to_channel(client: WebClient, channel: str, report: str, state: ESGTrendsState) -> None:
    """특정 채널에 리포트 전송

    Args:
        client: Slack WebClient
        channel: 채널 ID
        report: 리포트 내용
        state: 현재 상태
    """
    # 항상 메시지로 전송 (긴 리포트는 여러 메시지로 분할)
    _send_report_as_message(client, channel, report, state)


def _send_report_as_message(client: WebClient, channel: str, report: str, state: ESGTrendsState) -> None:
    """리포트를 메시지로 전송

    Args:
        client: Slack WebClient
        channel: 채널 ID
        report: 리포트 내용
        state: 현재 상태
    """
    from datetime import datetime

    today = datetime.now().strftime("%Y년 %m월 %d일")
    slack_report = _convert_to_slack_markdown(report)

    # 리포트를 섹션별로 분할 (## 기준)
    sections = _split_report_into_sections(slack_report)

    # 헤더 블록
    header_blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🌿 ESG 트렌드 일간 리포트",
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"발행일: {today}"
                }
            ]
        },
        {
            "type": "divider"
        }
    ]

    # 섹션들을 블록으로 변환 (각 블록은 3000자 제한)
    for section in sections:
        if section.strip():
            header_blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": section[:3000]
                }
            })

    try:
        logger.info(f"채널 {channel}에 메시지 전송 시도...")
        result = client.chat_postMessage(
            channel=channel,
            blocks=header_blocks,
            text="🌿 ESG 트렌드 일간 리포트"  # 폴백 텍스트
        )
        logger.info(f"✅ 메시지 전송 성공: {result.get('ts')}")
    except SlackApiError as e:
        error_msg = e.response.get('error', 'unknown')
        logger.error(f"Slack 메시지 전송 실패: {error_msg}")
        if error_msg == "not_in_channel":
            logger.error("봇이 채널에 초대되지 않았습니다. '/invite @봇이름' 실행 필요")
        elif error_msg == "channel_not_found":
            logger.error("채널을 찾을 수 없습니다. 채널 ID 확인 필요")
        elif error_msg == "missing_scope":
            logger.error("필요한 권한: chat:write")
        raise


def _split_report_into_sections(report: str) -> List[str]:
    """리포트를 섹션별로 분할

    Args:
        report: 전체 리포트 텍스트

    Returns:
        List[str]: 섹션별 텍스트 리스트
    """
    import re

    # ## 헤더 기준으로 분할
    sections = re.split(r'(?=\*[^*]+\*\n)', report)

    # 빈 섹션 제거 및 정리
    result = []
    for section in sections:
        section = section.strip()
        if section:
            result.append(section)

    # 섹션이 없으면 전체를 하나로
    if not result:
        result = [report]

    return result


def _upload_report_as_file(client: WebClient, channel: str, report: str, state: ESGTrendsState) -> None:
    """리포트를 파일로 업로드

    Args:
        client: Slack WebClient
        channel: 채널 ID
        report: 리포트 내용
        state: 현재 상태
    """
    from datetime import datetime

    filename = f"esg_report_{datetime.now().strftime('%Y%m%d')}.md"

    try:
        # 먼저 요약 메시지 전송
        summary = _create_summary_message(state)

        client.chat_postMessage(
            channel=channel,
            text=summary
        )

        # 파일 업로드
        client.files_upload_v2(
            channel=channel,
            content=report,
            filename=filename,
            title=f"ESG 트렌드 리포트 ({datetime.now().strftime('%Y-%m-%d')})",
            initial_comment="📎 상세 리포트"
        )

    except SlackApiError as e:
        logger.error(f"Slack 파일 업로드 실패: {e.response['error']}")
        raise


def _create_summary_message(state: ESGTrendsState) -> str:
    """요약 메시지 생성

    Args:
        state: 현재 상태

    Returns:
        str: 요약 메시지
    """
    weather_data = state.get("weather_data", [])
    domestic_news = state.get("domestic_news", [])
    global_news = state.get("global_news", [])
    physical_risks = state.get("physical_risks", [])
    trending_topics = state.get("trending_topics", [])

    # 고위험 리스크 확인
    high_risks = [r for r in physical_risks if r.get("risk_level") == "높음"]

    summary = "📊 *ESG 트렌드 일간 리포트 요약*\n\n"

    # 날씨 요약
    if weather_data:
        weather_str = ", ".join([
            f"{w.get('location')}: {w.get('temperature')}°C"
            for w in weather_data
        ])
        summary += f"🌤️ *날씨*: {weather_str}\n"

    # 리스크 알림
    if high_risks:
        risk_str = ", ".join([r.get("risk_type") for r in high_risks])
        summary += f"⚠️ *고위험 경고*: {risk_str}\n"

    # 뉴스 개수
    summary += f"📰 *뉴스 수집*: 국내 {len(domestic_news)}건, 글로벌 {len(global_news)}건\n"

    # 트렌드 키워드
    if trending_topics:
        topics_str = ", ".join(trending_topics[:5])
        summary += f"🔥 *트렌드*: {topics_str}\n"

    summary += "\n_상세 내용은 첨부 파일을 확인하세요._"

    return summary


def _convert_to_slack_markdown(text: str) -> str:
    """마크다운을 Slack 형식으로 변환

    Args:
        text: 원본 마크다운 텍스트

    Returns:
        str: Slack 마크다운 텍스트
    """
    # 기본적인 변환
    import re

    # 헤더 변환: ## -> *텍스트*
    text = re.sub(r'^#{1,6}\s+(.+)$', r'*\1*', text, flags=re.MULTILINE)

    # 볼드: **텍스트** -> *텍스트*
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)

    # 이탤릭: _텍스트_ 유지

    # 코드 블록 유지

    return text
