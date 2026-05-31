import xml.etree.ElementTree as ET
import os
import sys

def validate_podcast_feed(feed_file="feed.xml"):
    print(f"[🔍 Validate] '{feed_file}' 피드 유효성 검사를 시작합니다...")
    
    # 1. 파일 존재 여부 확인
    if not os.path.exists(feed_file):
        print(f"[❌ Fail] 피드 파일 '{feed_file}'이 존재하지 않습니다.")
        return False

    # 2. XML 기본 파싱 무결성 검증
    try:
        tree = ET.parse(feed_file)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"[❌ Fail] XML 문법 에러: {e}")
        return False
    except Exception as e:
        print(f"[❌ Fail] XML 파일을 읽는 도중 오류가 발생했습니다: {e}")
        return False

    # 3. 루트 및 채널 태그 확인
    if root.tag != "rss":
        print(f"[❌ Fail] 루트 엘리먼트가 'rss'가 아닙니다. (현재: {root.tag})")
        return False

    channel = root.find("channel")
    if channel is None:
        print("[❌ Fail] 'channel' 요소를 찾을 수 없습니다.")
        return False

    ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
    
    # 4. 필수 채널 메타데이터 태그 목록 검사
    required_channel_tags = ["title", "link", "description", "language"]
    for tag in required_channel_tags:
        el = channel.find(tag)
        if el is None or not el.text or not el.text.strip():
            print(f"[❌ Fail] 필수 채널 요소 '{tag}'가 누락되었거나 비어있습니다.")
            return False

    # 5. 필수 iTunes 채널 메타데이터 검사
    required_itunes_tags = [
        ("{%s}author" % ITUNES_NS, "itunes:author"),
        ("{%s}explicit" % ITUNES_NS, "itunes:explicit"),
    ]
    for tag_ns, tag_display in required_itunes_tags:
        el = channel.find(tag_ns)
        if el is None or not el.text or not el.text.strip():
            print(f"[❌ Fail] 필수 iTunes 요소 '{tag_display}'가 누락되었거나 비어있습니다.")
            return False

    # Category 속성 확인
    category = channel.find("{%s}category" % ITUNES_NS)
    if category is None or not category.get("text"):
        print("[❌ Fail] 필수 iTunes 요소 'itunes:category'가 없거나 'text' 속성이 설정되지 않았습니다.")
        return False

    # Owner 정보 확인
    owner = channel.find("{%s}owner" % ITUNES_NS)
    if owner is None:
        print("[❌ Fail] 필수 iTunes 요소 'itunes:owner'가 누락되었습니다.")
        return False
    else:
        o_name = owner.find("{%s}name" % ITUNES_NS)
        o_email = owner.find("{%s}email" % ITUNES_NS)
        if o_name is None or not o_name.text or not o_name.text.strip():
            print("[❌ Fail] 'itunes:owner' 내부의 'itunes:name'이 누락되었습니다.")
            return False
        if o_email is None or not o_email.text or not o_email.text.strip():
            print("[❌ Fail] 'itunes:owner' 내부의 'itunes:email'이 누락되었습니다.")
            return False

    # Cover Image 링크 속성 확인
    itunes_image = channel.find("{%s}image" % ITUNES_NS)
    if itunes_image is None or not itunes_image.get("href"):
        print("[❌ Fail] 필수 iTunes 이미지 요소 'itunes:image'가 없거나 'href' 속성이 설정되지 않았습니다.")
        return False

    # 6. 에피소드 아이템(Item) 요소 개별 무결성 검증
    items = channel.findall("item")
    print(f"[ℹ️ Info] 총 {len(items)}개의 에피소드 아이템이 감지되었습니다.")
    
    for idx, item in enumerate(items, 1):
        item_title = item.find("title")
        if item_title is None or not item_title.text or not item_title.text.strip():
            print(f"[❌ Fail] {idx}번째 에피소드 아이템의 'title'이 누락되었습니다.")
            return False

        title_text = item_title.text
        
        # enclosure 미디어 요소 체크
        enclosure = item.find("enclosure")
        if enclosure is None:
            print(f"[❌ Fail] 에피소드 '{title_text}'의 'enclosure' 미디어 태그가 누락되었습니다.")
            return False
        else:
            url = enclosure.get("url")
            m_type = enclosure.get("type")
            length = enclosure.get("length")
            
            if not url or not m_type or not length:
                print(f"[❌ Fail] 에피소드 '{title_text}'의 'enclosure' 속성(url, type, length) 중 일부가 누락되었습니다.")
                return False
            
            if not length.isdigit():
                print(f"[❌ Fail] 에피소드 '{title_text}'의 enclosure length 속성이 숫자가 아닙니다: {length}")
                return False

        # pubDate 및 guid 체크
        pubDate = item.find("pubDate")
        if pubDate is None or not pubDate.text or not pubDate.text.strip():
            print(f"[❌ Fail] 에피소드 '{title_text}'의 'pubDate' 발행일이 누락되었습니다.")
            return False

        guid = item.find("guid")
        if guid is None or not guid.text or not guid.text.strip():
            print(f"[❌ Fail] 에피소드 '{title_text}'의 'guid' 고유 식별자가 누락되었습니다.")
            return False

    print("[✅ Success] 모든 feed.xml 유효성 검사가 성공적으로 통과되었습니다!")
    return True

if __name__ == "__main__":
    target_feed = sys.argv[1] if len(sys.argv) > 1 else "feed.xml"
    success = validate_podcast_feed(target_feed)
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
