from fastapi import FastAPI, HTTPException, Response
import requests
import os
from pathlib import Path

# 1. 初始化 FastAPI 应用（保留 docs 便于调试，生产可关闭）
app = FastAPI(
    title="天气 SVG 图标服务",
    docs_url="/docs",  # Vercel 部署后可通过 https://你的域名/docs 访问调试文档
    redoc_url=None
)

# 2. 配置参数（SVG 路径为项目内相对路径，Vercel 中有效）
WEATHER_API_URL = "https://cloud-rest.lenovomm.com/cloud-weather/weather/localWeather"
SVG_STORAGE_DIR = "./weather"  # 与项目根目录下的 weather 文件夹对应

# 3. 确保 SVG 目录存在（Vercel 环境中项目目录可写，放心创建）
Path(SVG_STORAGE_DIR).mkdir(parents=True, exist_ok=True)

# 4. 核心接口（根路径，对应域名直接访问）
@app.get("/", response_class=Response)
async def get_weather_svg():
    try:
        # 步骤1：请求天气 API（注意：Vercel 允许外部请求，无需额外配置）
        weather_response = requests.get(WEATHER_API_URL, timeout=10)
        weather_response.raise_for_status()  # 捕获 API 4xx/5xx 错误
        weather_data = weather_response.json()

        # 步骤2：提取 weatherIndex（严格按 API 返回格式解析，避免 KeyError）
        weather_index = weather_data.get("data", [{}])[0].get("current", {}).get("weatherIndex")
        if not weather_index:
            raise HTTPException(status_code=404, detail="未从天气 API 获取到 weatherIndex 参数")

        # 步骤3：验证 SVG 文件是否存在（Vercel 中需确认文件已上传）
        svg_filename = f"{weather_index}.svg"
        svg_full_path = os.path.join(SVG_STORAGE_DIR, svg_filename)
        
        # 关键：Vercel 中需用 Path 确认文件存在（避免 os.path 兼容问题）
        if not Path(svg_full_path).exists():
            raise HTTPException(
                status_code=404,
                detail=f"未找到 SVG 图标：{svg_filename}（路径：{svg_full_path}）"
            )

        # 步骤4：读取 SVG 内容并返回（确保浏览器内联显示）
        with open(svg_full_path, "rb") as f:
            svg_data = f.read()

        return Response(
            content=svg_data,
            media_type="image/svg+xml",  # 必须正确设置，否则浏览器识别错误
            headers={
                "Content-Disposition": f"inline; filename={svg_filename}",
                "Content-Length": str(Path(svg_full_path).stat().st_size)  # 用 Path 获取文件大小
            }
        )

    # 异常处理（明确错误信息，便于在 Vercel 日志中排查）
    except requests.exceptions.RequestException as e:
        # 捕获天气 API 请求错误（如超时、连接失败）
        raise HTTPException(status_code=500, detail=f"天气 API 请求失败：{str(e)}")
    except Exception as e:
        # 捕获其他未知错误（如文件读取失败）
        raise HTTPException(status_code=500, detail=f"服务器异常：{str(e)}")
