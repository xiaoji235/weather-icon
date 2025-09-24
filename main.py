from fastapi import FastAPI, HTTPException, Response
import requests
import os
from pathlib import Path

# 初始化 FastAPI 应用
app = FastAPI(title="天气 SVG 图标服务")

# 配置参数
WEATHER_API_URL = "https://cloud-rest.lenovomm.com/cloud-weather/weather/localWeather"
SVG_STORAGE_DIR = "./weather"  # SVG 文件存放路径

# 确保 SVG 目录存在
Path(SVG_STORAGE_DIR).mkdir(parents=True, exist_ok=True)

@app.get("/", response_class=Response)
async def get_weather_svg():
    try:
        # 1. 请求天气 API 获取数据
        weather_response = requests.get(WEATHER_API_URL, timeout=10)
        weather_response.raise_for_status()  # 检查请求是否成功
        weather_data = weather_response.json()
        
        # 2. 提取 weatherIndex 参数
        weather_index = weather_data.get("data", [{}])[0].get("current", {}).get("weatherIndex")
        
        if not weather_index:
            raise HTTPException(status_code=404, detail="未获取到 weatherIndex 参数")
        
        # 3. 构建 SVG 文件路径并检查是否存在
        svg_filename = f"{weather_index}.svg"
        svg_full_path = os.path.join(SVG_STORAGE_DIR, svg_filename)
        
        if not os.path.exists(svg_full_path):
            raise HTTPException(
                status_code=404, 
                detail=f"未找到 SVG 图标：{svg_filename}（路径：{svg_full_path}）"
            )
        
        # 4. 读取 SVG 文件内容并构建响应
        with open(svg_full_path, "rb") as f:
            svg_data = f.read()
        
        # 返回响应，设置正确的内容类型和响应头
        return Response(
            content=svg_data,
            media_type="image/svg+xml",
            headers={
                "Content-Disposition": f"inline; filename={svg_filename}",
                "Content-Length": str(os.path.getsize(svg_full_path))
            }
        )
    
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"天气 API 请求失败：{str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器错误：{str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
    
