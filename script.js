document.getElementById('generate').addEventListener('click', async () => {
    const articleUrl = document.getElementById('articleUrl').value;
    const wordCount = document.getElementById('wordCount').value;
    const tone = document.getElementById('tone').value;
    const style = document.getElementById('style').value;
    const result = document.getElementById('result');
    
    console.log("开始生成短视频口播文案...");
    result.textContent = '正在生成...';
    
    try {
        console.log("发送请求到后端...");
        const response = await fetch('/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ articleUrl, wordCount, tone, style }),
        });
        
        console.log("收到后端响应");
        const data = await response.json();
        
        if (response.ok) {
            result.textContent = data.script;
        } else {
            result.textContent = data.error || '生成失败，请重试。';
        }
    } catch (error) {
        console.error("发生错误:", error);
        result.textContent = '发生错误，请重试。';
    }
});