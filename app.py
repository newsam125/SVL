from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import logging
from langdetect import detect
import json

app = Flask(__name__, static_folder='.')
CORS(app)

logging.basicConfig(level=logging.DEBUG)

LINKAI_API_KEY = "Link_42NOukf0cW0D3iysRo3UNbFsQfwlAx7enRYUIhmRUG"

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

def get_zhihu_content(url):
    try:
        # 尝试多种URL格式
        patterns = [
            r'question/(\d+)/answer/(\d+)',  # 标准问答格式
            r'zhuanlan\.zhihu\.com/p/(\d+)',  # 专栏文章格式
            r'/(\d+)',  # 短URL格式
        ]
        
        question_id = None
        answer_id = None
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                if len(match.groups()) == 2:
                    question_id, answer_id = match.groups()
                    break
                elif len(match.groups()) == 1:
                    answer_id = match.group(1)
                    break
        
        if not answer_id:
            return None, "无法从URL中提取必要的ID"
        
        # 构造API URL
        if question_id:
            api_url = f"https://www.zhihu.com/api/v4/questions/{question_id}/answers/{answer_id}"
        else:
            api_url = f"https://www.zhihu.com/api/v4/articles/{answer_id}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(api_url, headers=headers)
        if response.status_code != 200:
            return None, f"API请求失败，状态码：{response.status_code}"
        
        data = response.json()
        
        # 提取标题和内容
        if 'question' in data:
            title = data['question']['title']
            content = data['content']
        else:
            title = data['title']
            content = data['content']
        
        # 使用BeautifulSoup清理HTML标签
        soup = BeautifulSoup(content, 'html.parser')
        text_content = soup.get_text(separator=' ', strip=True)
        
        return title, text_content
    except Exception as e:
        return None, f"处理知乎内容时发生错误：{str(e)}"

def get_article_content(url, max_length):
    try:
        logging.info(f"尝试获取文章内容: {url}")
        
        if 'zhihu.com' in url:
            title, content = get_zhihu_content(url)
            if title and content:
                summary = content[:max_length]
                return title, summary
            else:
                return "错误", content  # content 在这里包含错误信息
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = soup.find('title')
        content = soup.find_all('p')
        
        if title and content:
            title = title.text.strip() if title else "无标题"
            content = ' '.join([p.text for p in content if p.text])
            content = re.sub(r'\s+', ' ', content)
            summary = content[:max_length]
            return title, summary
        else:
            return "无标题", "无法找到文章的内容"
    except Exception as e:
        logging.error(f"获取文章内容时发生错误: {str(e)}")
        return "错误", str(e)

def generate_script_with_length_control(prompt, target_length, max_attempts=3):
    for attempt in range(max_attempts):
        logging.info(f"尝试生成文案，第 {attempt + 1} 次")
        linkai_response = requests.post(
            "https://api.link-ai.chat/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {LINKAI_API_KEY}"
            },
            json={
                "model": "LinkAI-4o",
                "messages": [
                    {"role": "system", "content": "你是一个专业的短视频口播文案编写者，擅长将文章内容转化为吸引人的短视频口播文案。"},
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=30
        )
        
        if linkai_response.status_code == 200:
            script = linkai_response.json()['choices'][0]['message']['content']
            current_length = len(script)
            logging.info(f"生成的文案长度: {current_length}")
            
            if abs(current_length - target_length) <= target_length * 0.1:  # 允许10%的误差
                return script
            elif current_length > target_length:
                prompt += f"\n请注意控制文案长度，目标长度为{target_length}字，当前生成的文案过长。"
            else:
                prompt += f"\n请适当增加文案长度，目标长度为{target_length}字，当前生成的文案过短。"
        else:
            logging.error(f"LinkAI API调用失败，状态码：{linkai_response.status_code}")
            return None
    
    logging.warning(f"无法生成符合长度要求的文案，返回最后一次生成的结果")
    return script

@app.route('/generate', methods=['POST'])
def generate_script():
    try:
        data = request.json
        article_url = data.get('articleUrl')
        word_count = int(data.get('wordCount'))
        tone = data.get('tone')
        style = data.get('style')
        
        logging.info(f"收到生成请求: URL={article_url}, 字数={word_count}, 语气={tone}, 风格={style}")
        
        max_length = word_count * 3
        
        title, summary = get_article_content(article_url, max_length)
        
        if title == "错误":
            return jsonify({"error": f"无法获取文章内容：{summary}"}), 400
        
        logging.info(f"成功获取文章内容: 标题={title}, 摘要长度={len(summary)}")
        
        try:
            lang = detect(summary)
        except:
            lang = 'zh'  # 如果检测失败，默认为中文
        
        if lang != 'zh':
            translation_prompt = f"请将以下内容翻译成中文：\n标题：{title}\n内容：{summary}\n然后根据翻译后的内容生成短视频口播文案。"
        else:
            translation_prompt = ""
        
        prompt = f"""{translation_prompt}
        请根据以下内容生成一个短视频口播文案。
        标题：{title}
        内容概要：{summary}
        要求：
        1. 字数限制在{word_count}字左右，请严格控制在此范围内
        2. 使用{tone}的语气
        3. 采用{style}的表达方式
        4. 适合短视频口播，吸引观众注意力
        请确保生成的口播文案简洁明了，适合短视频配音。"""
        
        logging.info("开始生成文案")
        script = generate_script_with_length_control(prompt, word_count)
        
        if script:
            logging.info(f"成功生成口播文案，长度: {len(script)}")
            return jsonify({"script": script})
        else:
            error_message = "无法生成符合要求的文案"
            logging.error(error_message)
            return jsonify({"error": error_message}), 500
        
    except Exception as e:
        error_message = f"发生错误: {str(e)}"
        logging.error(error_message)
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)