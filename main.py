from fastapi import FastAPI, HTTPException, Response
import requests
import os
from pathlib import Path

app = FastAPI(
    title="天气 SVG 图标服务",
    docs_url="/docs"
)

# 配置参数
WEATHER_API_URL = "https://cloud-rest.lenovomm.com/cloud-weather/weather/localWeather"
SVG_STORAGE_DIR = "./weather"

# 确保SVG目录存在
Path(SVG_STORAGE_DIR).mkdir(parents=True, exist_ok=True)

@app.get("/", response_class=Response)
async def get_weather_svg():
    try:
        # 1. 请求天气API并检查响应
        weather_response = requests.get(WEATHER_API_URL, timeout=10)
        weather_response.raise_for_status()
        
        # 2. 解析JSON数据（增加空值检查）
        weather_data = weather_response.json()
        if not weather_data:
            raise HTTPException(status_code=500, detail="天气API返回空数据")
        
        # 3. 安全提取data数组（防止data为None或非数组）
        data_list = weather_data.get("data")
        if not isinstance(data_list, list) or len(data_list) == 0:
            raise HTTPException(status_code=500, detail="天气API返回数据格式错误（data不是有效数组）")
        
        # 4. 提取第一个数据项
        first_data = data_list[0]
        if not isinstance(first_data, dict):
            raise HTTPException(status_code=500, detail="天气API返回数据格式错误（data项不是对象）")
        
        # 5. 提取current对象（关键修复：增加多层空值检查）
        current_data = first_data.get("current")
        if not isinstance(current_data, dict):
            raise HTTPException(status_code=500, detail="天气API返回数据格式错误（current不是有效对象）")
        
        # 6. 提取weatherIndex
        weather_index = current_data.get("weatherIndex")
        if not weather_index:
            raise HTTPException(status_code=404, detail="未从天气API获取到weatherIndex参数")
        
        # 7. 检查SVG文件
        svg_filename = f"{weather_index}.svg"
        svg_full_path = os.path.join(SVG_STORAGE_DIR, svg_filename)
        
        if not Path(svg_full_path).exists():
            raise HTTPException(
                status_code=404,
                detail=f"未找到SVG图标：{svg_filename}（路径：{svg_full_path}）"
            )
        
        # 8. 返回SVG内容
        with open(svg_full_path, "rb") as f:
            svg_data = f.read()
        
        return Response(
            content=svg_data,
            media_type="image/svg+xml",
            headers={
                "Content-Disposition": f"inline; filename={svg_filename}",
                "Content-Length": str(Path(svg_full_path).stat().st_size)
            }
        )
    
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"天气API请求失败：{str(e)}")
    except HTTPException as e:
        # 重新抛出已定义的HTTP异常
        raise e
    except Exception as e:
        # 捕获其他未预料的错误
        raise HTTPException(status_code=500, detail=f"服务器异常：{str(e)}")
