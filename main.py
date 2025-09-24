from fastapi import FastAPI, HTTPException, Response, Query
import requests
import os
from pathlib import Path
import json

app = FastAPI(
    title="带城市参数的天气SVG图标服务",
    docs_url="/docs"
)

# 配置参数
WEATHER_API_URL = "https://cloud-rest.lenovomm.com/cloud-weather/weather/localWeather"
SVG_STORAGE_DIR = "./weather"

# 确保SVG目录存在
Path(SVG_STORAGE_DIR).mkdir(parents=True, exist_ok=True)

@app.get("/", response_class=Response)
async def get_weather_svg(
    city: str = Query(..., description="要查询的城市名称，如'北京'、'上海'")
):
    try:
        # 1. 向天气API发送请求，传递城市参数
        # 注意：根据实际API文档调整参数名（可能是city、cityname等）
        params = {"city": city}
        weather_response = requests.get(
            WEATHER_API_URL,
            params=params,
            timeout=10
        )
        weather_response.raise_for_status()
        
        # 2. 处理API响应
        raw_response_text = weather_response.text
        print(f"天气API响应({city}): {raw_response_text}")
        
        try:
            weather_data = weather_response.json()
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=500,
                detail=f"API返回非JSON格式: {str(e)}\n内容: {raw_response_text[:200]}"
            )
        
        # 3. 检查API返回状态码
        api_code = weather_data.get("code")
        if api_code != "10000":
            raise HTTPException(
                status_code=500,
                detail=f"天气API错误({city}): {weather_data.get('message')}（code: {api_code}）"
            )
        
        # 4. 验证data字段
        data_list = weather_data.get("data")
        if not isinstance(data_list, list) or len(data_list) == 0:
            raise HTTPException(
                status_code=500,
                detail=f"{city}的data不是有效数组（类型: {type(data_list).__name__}）"
            )
        
        # 5. 提取weatherIndex
        first_data = data_list[0]
        current_data = first_data.get("current", {})
        weather_index = current_data.get("weatherIndex")
        
        if not weather_index:
            raise HTTPException(status_code=404, detail=f"{city}未找到weatherIndex参数")
        
        # 6. 返回SVG图标
        svg_filename = f"{weather_index}.svg"
        svg_full_path = os.path.join(SVG_STORAGE_DIR, svg_filename)
        
        if not Path(svg_full_path).exists():
            raise HTTPException(
                status_code=404,
                detail=f"未找到{weather_index}.svg（城市: {city}）"
            )
        
        with open(svg_full_path, "rb") as f:
            svg_data = f.read()
        
        return Response(
            content=svg_data,
            media_type="image/svg+xml",
            headers={"Content-Disposition": f"inline; filename={city}_{svg_filename}"}
        )
    
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API请求失败({city}): {str(e)}")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器异常({city}): {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)
