const apiKey = 'Link_42NOukf0cW0D3iysRo3UNbFsQfwlAx7enRYUIhmRUG';

document.getElementById('inputForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const url = document.getElementById('urlInput').value;
    const manualContent = document.getElementById('contentInput').value;
    const customTone = document.getElementById('customTone').value;
    const customStyle = document.getElementById('customStyle').value;
    const tone = customTone || document.getElementById('toneSelect').value;
    const style = customStyle || document.getElementById('styleSelect').value;
    const wordCount = document.getElementById('wordCountSelect').value;

    let content;
    if (manualContent) {
        content = manualContent;
    } else if (url) {
        try {
            content = await fetchArticleContent(url);
        } catch (error) {
            console.error('获取文章内容失败:', error);
            alert('无法自动获取文章内容。请直接将文章内容复制粘贴到文本框中。');
            return;
        }
    } else {
        alert('请输入文章URL或直接粘贴文章内容');
        return;
    }

    try {
        const script = await generateScript(content, tone, style, wordCount);
        document.getElementById('output').innerText = script;
        document.getElementById('outputContainer').style.display = 'block';
    } catch (error) {
        console.error('生成讲稿失败:', error);
        alert('生成讲稿失败: ' + error.message);
    }
});

// 添加复制功能
document.getElementById('copyButton').addEventListener('click', () => {
    const outputText = document.getElementById('output').innerText;
    navigator.clipboard.writeText(outputText).then(() => {
        alert('讲稿已复制到剪贴板');
    }, (err) => {
        console.error('无法复制文本: ', err);
    });
});

async function fetchArticleContent(url) {
    try {
        console.log('正在获取文章内容...');
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const htmlContent = await response.text();
        
        // 创建一个 DOMParser 对象
        const parser = new DOMParser();
        const doc = parser.parseFromString(htmlContent, 'text/html');
        
        // 尝试提取文章内容
        let content = '';
        
        // 尝试提取标题
        const titleElement = doc.querySelector('.article-title');
        if (titleElement) {
            content += '标题: ' + titleElement.textContent.trim() + '\n\n';
        }
        
        // 尝试提取正文
        const contentElement = doc.querySelector('.article-content');
        if (contentElement) {
            content += contentElement.textContent.trim();
        }
        
        if (!content) {
            // 如果无法提取内容，返回整个body的文本
            content = doc.body.textContent.trim();
        }
        
        console.log('成功获取文章内容,长度:', content.length);
        return content;
    } catch (error) {
        console.error('获取文章内容错误:', error);
        alert('无法自动获取文章内容。请直接将文章内容复制粘贴到下方的文本框中。');
        throw error;
    }
}

function truncateContent(content, maxLength = 100000) {
    if (content.length <= maxLength) return content;
    return content.substring(0, maxLength) + '...（内容已截断）';
}

async function generateScript(content, tone, style, wordCount) {
    try {
        console.log('正在发送请求...');
        const truncatedContent = truncateContent(content);
        const response = await fetch('https://api.link-ai.chat/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`
            },
            body: JSON.stringify({
                model: "LinkAI-4o",
                messages: [
                    { role: 'system', content: `你是一个${style}专家。请用${tone}的语气为以下内容生成一个简洁的短视频口播讲稿。要求：
1. 讲稿应该简洁明了,适合口述。
2. 不要包含任何镜头画面描述或多余的解说。
3. 只使用中文,如果有其他语言请翻译成中文。
4. 保持口语化,易于理解和朗读。
5. 突出重点内容,避免冗长的解释。
6. 讲稿的字数必须严格控制在${wordCount}字左右,请精确控制。` },
                    { role: 'user', content: truncatedContent }
                ],
                temperature: 0.7,
                top_p: 1,
                frequency_penalty: 0,
                presence_penalty: 0
            }),
        });
        console.log('收到响应:', response.status);
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API请求失败: ${response.status} ${errorText}`);
        }
        const result = await response.json();
        if (result.choices && result.choices.length > 0) {
            const generatedContent = result.choices[0].message.content;
            console.log('生成的内容长度:', generatedContent.length);
            return generatedContent;
        } else {
            throw new Error('API返回的数据结构不正确');
        }
    } catch (error) {
        console.error('生成讲稿错误:', error);
        throw error;
    }
}