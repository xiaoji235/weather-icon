from fastapi import FastAPI, HTTPException, Response
import requests
import os
from pathlib import Path
import json  # 用于格式化输出调试信息

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
        # 1. 请求天气API并获取原始响应内容
        weather_response = requests.get(WEATHER_API_URL, timeout=10)
        weather_response.raise_for_status()  # 检查HTTP状态码（如404、500等）
        
        # 2. 保存原始响应内容用于调试
        raw_response_text = weather_response.text
        print(f"天气API原始响应: {raw_response_text}")  # 部署后可在Vercel日志中查看
        
        # 3. 解析JSON数据
        try:
            weather_data = weather_response.json()
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=500,
                detail=f"天气API返回内容不是有效的JSON格式: {str(e)}\n原始内容: {raw_response_text[:200]}"  # 显示前200字符
            )
        
        # 4. 验证data字段是否为有效数组
        data_list = weather_data.get("data")
        # 详细调试信息：输出data字段的类型和值
        print(f"data字段类型: {type(data_list)}, 值: {data_list}")
        
        # 严格验证：必须是数组且至少有一个元素
        if not isinstance(data_list, list) or len(data_list) == 0:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"天气API返回的data不是有效数组（类型: {type(data_list).__name__}）\n"
                    f"原始响应: {raw_response_text[:200]}"  # 显示部分原始内容便于排查
                )
            )
        
        # 5. 后续逻辑与之前相同（提取current和weatherIndex）
        first_data = data_list[0]
        if not isinstance(first_data, dict):
            raise HTTPException(
                status_code=500,
                detail=f"data数组第一个元素不是对象（类型: {type(first_data).__name__}）"
            )
        
        current_data = first_data.get("current")
        if not isinstance(current_data, dict):
            raise HTTPException(
                status_code=500,
                detail=f"current不是有效对象（类型: {type(current_data).__name__}）"
            )
        
        weather_index = current_data.get("weatherIndex")
        if not weather_index:
            raise HTTPException(status_code=404, detail="未从天气API获取到weatherIndex参数")
        
        # 6. 检查并返回SVG文件
        svg_filename = f"{weather_index}.svg"
        svg_full_path = os.path.join(SVG_STORAGE_DIR, svg_filename)
        
        if not Path(svg_full_path).exists():
            raise HTTPException(
                status_code=404,
                detail=f"未找到SVG图标：{svg_filename}（路径：{svg_full_path}）"
            )
        
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
        raise HTTPException(
            status_code=500,
            detail=f"天气API请求失败: {str(e)}\n可能是网络问题或API地址错误"
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器异常：{str(e)}")
