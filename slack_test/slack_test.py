"""Slack 발송 테스트 스크립트"""
import os
import logging
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def test_slack():
    token = os.getenv("SLACK_BOT_TOKEN")
    channel = os.getenv("SLACK_CHANNEL", "auto")

    if not token:
        logger.error("SLACK_BOT_TOKEN이 설정되지 않았습니다")
        return

    logger.info(f"토큰: {token[:20]}...")
    logger.info(f"채널 설정: {channel}")

    client = WebClient(token=token)

    # 1. 봇 정보 확인
    logger.info("봇 정보 확인 중...")
    try:
        auth = client.auth_test()
        logger.info(f"봇 이름: {auth.get('user')}")
        logger.info(f"봇 ID: {auth.get('user_id')}")
        logger.info(f"워크스페이스: {auth.get('team')}")
        bot_name = auth.get('user')
    except SlackApiError as e:
        logger.error(f"인증 실패: {e.response.get('error')}")
        return

    # 2. 채널 목록 조회 (페이지네이션 포함)
    if channel.lower() == "auto":
        logger.info("채널 목록 조회 중...")
        try:
            all_channels = []
            cursor = None

            while True:
                result = client.conversations_list(
                    types="public_channel,private_channel",
                    exclude_archived=True,
                    limit=200,
                    cursor=cursor
                )
                channels = result.get("channels", [])
                all_channels.extend(channels)

                cursor = result.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break

            logger.info(f"총 {len(all_channels)}개 채널 발견")

            target_channels = []
            for ch in all_channels:
                name = ch.get("name", "unknown")
                is_member = ch.get("is_member", False)
                is_private = ch.get("is_private", False)
                ch_type = "Private" if is_private else "Public"
                logger.info(f"  #{name} ({ch_type}): is_member={is_member}")
                if is_member:
                    target_channels.append({"id": ch["id"], "name": name})

            if not target_channels:
                logger.warning("봇이 멤버인 채널이 없습니다.")
                logger.warning(f"채널에서 '/invite @{bot_name}'으로 초대하세요")
                return

            logger.info(f"봇이 멤버인 채널: {len(target_channels)}개")
            for ch in target_channels:
                logger.info(f"  - #{ch['name']}")

        except SlackApiError as e:
            error = e.response.get('error')
            logger.error(f"채널 목록 조회 실패: {error}")
            if error == "missing_scope":
                logger.error("필요한 권한: channels:read, groups:read")
            elif error == "invalid_auth":
                logger.error("토큰이 유효하지 않습니다")
            return
    else:
        target_channels = [{"id": channel, "name": channel}]

    # 3. 메시지 전송
    for ch in target_channels:
        ch_id = ch["id"]
        ch_name = ch["name"]
        logger.info(f"#{ch_name} 채널에 메시지 전송 중...")
        try:
            result = client.chat_postMessage(
                channel=ch_id,
                text="슬랙 발송 테스트"
            )
            logger.info(f"메시지 전송 성공: ts={result.get('ts')}")
        except SlackApiError as e:
            error = e.response.get('error')
            logger.error(f"메시지 전송 실패: {error}")
            if error == "not_in_channel":
                logger.error("봇이 채널에 초대되지 않았습니다")
            elif error == "channel_not_found":
                logger.error("채널을 찾을 수 없습니다")
            elif error == "missing_scope":
                logger.error("chat:write 권한이 필요합니다")


if __name__ == "__main__":
    test_slack()
