import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import os
import sys
import subprocess
import re
import yaml

def get_git_remote_url():
    """로컬 Git 설정에서 origin remote URL을 조회합니다."""
    try:
        url = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"], 
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        return url
    except Exception:
        return None

def infer_base_url():
    """Git remote origin URL을 기반으로 GitHub Pages 기본 URL을 자동 추론합니다."""
    remote_url = get_git_remote_url()
    if not remote_url:
        print("[⚠️ Warning] Git origin URL을 감지하지 못했습니다. 로컬 환경 테스트용 기본 주소를 사용합니다.")
        return "https://username.github.io/my-podcast/"

    # SSH 포맷: git@github.com:username/repo.git
    ssh_match = re.match(r"git@github\.com:([^/]+)/([^.]+)(?:\.git)?", remote_url)
    if ssh_match:
        owner = ssh_match.group(1)
        repo = ssh_match.group(2)
        return f"https://{owner}.github.io/{repo}/"

    # HTTPS 포맷: https://github.com/username/repo.git 또는 https://github.com/username/repo
    https_match = re.match(r"https://github\.com/([^/]+)/([^/.]+)(?:\.git)?", remote_url)
    if https_match:
        owner = https_match.group(1)
        repo = https_match.group(2)
        return f"https://{owner}.github.io/{repo}/"

    # 기타 매칭 실패 시 원본 리턴
    print(f"[⚠️ Warning] Git Remote URL 포맷({remote_url})을 해석할 수 없습니다. 그대로 사용합니다.")
    return remote_url

def update_podcast_feed(title, audio_filename, description):
    feed_file = "feed.xml"
    config_file = "config.yaml"
    
    # 1. config.yaml 로드
    if not os.path.exists(config_file):
        print(f"[❌ Error] 설정 파일({config_file})이 존재하지 않습니다. 먼저 설정을 만들어주세요.")
        sys.exit(1)
        
    with open(config_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 2. base_url 세팅 (설정 파일에 없으면 자동 추론)
    base_url = config.get("base_url", "")
    if not base_url:
        base_url = infer_base_url()
    
    # URL 끝에 슬래시(/)가 포함되도록 보정
    if not base_url.endswith("/"):
        base_url += "/"
        
    print(f"[ℹ️ Info] 호스팅 Base URL: {base_url}")
    
    audio_url = base_url + "audio/" + audio_filename
    image_url = base_url + "cover.png"
    
    ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
    ET.register_namespace("itunes", ITUNES_NS)
    
    # 3. feed.xml 파싱 또는 신규 생성
    if not os.path.exists(feed_file):
        print(f"[ℹ️ Info] {feed_file} 파일이 존재하지 않아 새로 생성합니다.")
        rss = ET.Element("rss", version="2.0")
        rss.set("xmlns:itunes", ITUNES_NS)
        channel = ET.SubElement(rss, "channel")
        
        ET.SubElement(channel, "title").text = config.get("title", "My AI Podcast")
        ET.SubElement(channel, "link").text = base_url
        ET.SubElement(channel, "description").text = config.get("description", "AI Generated Podcast")
        ET.SubElement(channel, "language").text = config.get("language", "ko-KR")
        
        ET.SubElement(channel, "{%s}author" % ITUNES_NS).text = config.get("author", "AI Agent")
        ET.SubElement(channel, "{%s}explicit" % ITUNES_NS).text = "false"
        
        category = ET.SubElement(channel, "{%s}category" % ITUNES_NS)
        category.set("text", config.get("category", "Technology"))
        
        itunes_owner = ET.SubElement(channel, "{%s}owner" % ITUNES_NS)
        owner_config = config.get("owner", {})
        ET.SubElement(itunes_owner, "{%s}name" % ITUNES_NS).text = owner_config.get("name", "AI Agent")
        ET.SubElement(itunes_owner, "{%s}email" % ITUNES_NS).text = owner_config.get("email", "agent@example.com")
        
        # 팟캐스트 커버 등록
        itunes_image = ET.SubElement(channel, "{%s}image" % ITUNES_NS)
        itunes_image.set("href", image_url)
    else:
        print(f"[ℹ️ Info] 기존 {feed_file} 파일을 수정합니다.")
        tree = ET.parse(feed_file)
        rss = tree.getroot()
        channel = rss.find("channel")
        
        # 기존 메타데이터 설정값 기반 동기화 (안전하게 없을 경우 새로 생성)
        def set_text_or_create(parent, tag, text):
            el = parent.find(tag)
            if el is None:
                el = ET.SubElement(parent, tag)
            el.text = text

        set_text_or_create(channel, "title", config.get("title", "My AI Podcast"))
        set_text_or_create(channel, "link", base_url)
        set_text_or_create(channel, "description", config.get("description", "AI Generated Podcast"))
        set_text_or_create(channel, "language", config.get("language", "ko-KR"))
        set_text_or_create(channel, "{%s}author" % ITUNES_NS, config.get("author", "AI Agent"))
        
        it_owner = channel.find("{%s}owner" % ITUNES_NS)
        if it_owner is None:
            it_owner = ET.SubElement(channel, "{%s}owner" % ITUNES_NS)
        owner_config = config.get("owner", {})
        set_text_or_create(it_owner, "{%s}name" % ITUNES_NS, owner_config.get("name", "AI Agent"))
        set_text_or_create(it_owner, "{%s}email" % ITUNES_NS, owner_config.get("email", "agent@example.com"))
        
        it_image = channel.find("{%s}image" % ITUNES_NS)
        if it_image is None:
            it_image = ET.SubElement(channel, "{%s}image" % ITUNES_NS)
        it_image.set("href", image_url)

    # 4. 신규 에피소드 아이템(Item) 생성 및 주입
    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = title
    
    file_path = os.path.join("audio", audio_filename)
    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    
    # 팟캐스트 포맷에 맞춘 MIME Type 감지
    mime_type = "audio/x-m4a" if audio_filename.lower().endswith(".m4a") else "audio/mpeg"
    ET.SubElement(item, "enclosure", url=audio_url, type=mime_type, length=str(file_size))
    
    # 한국 표준시(KST) 시간 기준 pubDate 설정
    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst)
    ET.SubElement(item, "pubDate").text = now_kst.strftime("%a, %d %b %Y %H:%M:%S +0900")
    
    ET.SubElement(item, "description").text = description
    ET.SubElement(item, "{%s}summary" % ITUNES_NS).text = description
    ET.SubElement(item, "guid", isPermaLink="false").text = audio_url
    ET.SubElement(item, "{%s}explicit" % ITUNES_NS).text = "false"

    # 중복 선언된 네임스페이스 제거 정제
    xml_str = ET.tostring(rss, encoding="utf-8").decode("utf-8")
    if xml_str.count("xmlns:itunes") > 1:
        rss.attrib.pop("xmlns:itunes", None)
        xml_str = ET.tostring(rss, encoding="utf-8").decode("utf-8")

    # XML 덮어쓰기 저장
    with open(feed_file, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(xml_str)
        
    print(f"[✅ Success] {feed_file} 업데이트가 완료되었습니다.")
    print(f"            - 에피소드 제목: {title}")
    print(f"            - 파일명: {audio_filename}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python scripts/update_feed.py <title> <audio_filename> <description>")
    else:
        update_podcast_feed(sys.argv[1], sys.argv[2], sys.argv[3])
