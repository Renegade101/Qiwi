from fastapi import FastAPI, HTTPException, Response, UploadFile, File
import requests
import xmltodict
import json
import logging

logging.basicConfig(level=logging.DEBUG)

app = FastAPI()

# Создаем кэш
cache = {}
@app.post("/proxy")
@app.put("/proxy")
async def proxy_request(request_data: dict):
    cache_key = str({k: v for k, v in request_data.items() if k != "id"})

    if cache_key in cache:
        cached_response = cache[cache_key].copy()
        cached_response["id"] = request_data.get("id", "")
        return cached_response

    partner_url = request_data.get("redirect_url", "")
    if not partner_url:
        raise HTTPException(status_code=400, detail="Partner URL is not provided")

    response = requests.post(partner_url, json=request_data)

    if response.status_code == 200:
        if "application/json" in response.headers["Content-Type"]:
            partner_response = response.json()
        elif "application/xml" in response.headers["Content-Type"]:
            partner_response = xmltodict.parse(response.text)
        else:
            raise HTTPException(status_code=500, detail="Unsupported response format")

        # Сохраняем кэш
        cache[cache_key] = partner_response
        logging.debug(f"Cache Key: {cache_key}")
        logging.debug(f"Request Data: {request_data}")
        logging.debug(f"Cache Contents: {cache}")
        partner_response["id"] = request_data.get("id", "")
        return partner_response
    else:
        raise HTTPException(status_code=response.status_code, detail="Partner request failed")

@app.delete("/clear_cache")
async def clear_cache():
    cache.clear()
    return {"message": "Cache cleared"}

@app.get("/export_cache")
async def export_cache():
    response_content = json.dumps(cache, ensure_ascii=False, indent=2)
    response = Response(content=response_content, media_type="application/json")
    response.headers["Content-Disposition"] = 'attachment; filename="cache_export.json"'
    return response

@app.post("/import_cache")
async def import_cache(file: UploadFile = File(...)):
    content = await file.read()
    loaded_cache = json.loads(content)
    cache.update(loaded_cache)
    logging.debug(f"Cache Key: {cache_key}")
    logging.debug(f"Request Data: {request_data}")
    logging.debug(f"Cache Contents: {cache}")
    return {"message": "Cache imported successfully"}

if __name__ == "__main__":
    import uvicorn

    # Запускаем сервер на порту 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)