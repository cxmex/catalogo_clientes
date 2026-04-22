from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import httpx
import asyncio

app = FastAPI(title="Catalogo Fundastock")
templates = Jinja2Templates(directory="templates")

SUPABASE_URL = "https://gbkhkbfbarsnpbdkxzii.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdia2hrYmZiYXJzbnBiZGt4emlpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzQzODAzNzMsImV4cCI6MjA0OTk1NjM3M30.mcOcC2GVEu_wD3xNBzSCC3MwDck3CIdmz4D8adU-bpI"
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}
STORAGE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}


@app.get("/", response_class=HTMLResponse)
async def catalogo(request: Request):
    """Customer-facing catalog: stock by estilo/modelo with images."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp_stock_estilo, resp_stock_detail, resp_stock_color, resp_estilos, resp_modelos = await asyncio.gather(
                client.get(f"{SUPABASE_URL}/rest/v1/rpc/get_current_stock_by_estilo", headers=HEADERS),
                client.get(f"{SUPABASE_URL}/rest/v1/rpc/get_current_stock_by_estilo_modelo", headers=HEADERS),
                client.get(f"{SUPABASE_URL}/rest/v1/rpc/get_current_stock_by_estilo_modelo_color", headers=HEADERS),
                client.get(
                    f"{SUPABASE_URL}/rest/v1/inventario_estilos",
                    headers={**HEADERS, "Range": "0-999"},
                    params={"select": "id,nombre", "limit": "1000"}
                ),
                client.get(
                    f"{SUPABASE_URL}/rest/v1/inventario_modelos",
                    headers={**HEADERS, "Range": "0-9999"},
                    params={"select": "id,modelo,marca", "order": "modelo.asc"}
                ),
            )

        # Build estilo name -> id map for image links
        estilo_ids = {}
        if resp_estilos.status_code < 400:
            for e in resp_estilos.json():
                estilo_ids[e.get("nombre", "")] = e.get("id")

        stock_by_estilo = resp_stock_estilo.json() if resp_stock_estilo.status_code < 400 else []

        stock_detail = {}
        if resp_stock_detail.status_code < 400:
            for r in resp_stock_detail.json():
                est = r.get("estilo", "")
                if est not in stock_detail:
                    stock_detail[est] = []
                stock_detail[est].append({
                    "modelo": r.get("modelo", ""),
                    "t1": int(r.get("terex1_stock", 0) or 0),
                    "t2": int(r.get("terex2_stock", 0) or 0),
                    "total": int(r.get("total_stock", 0) or 0),
                })

        color_detail = {}
        if resp_stock_color.status_code < 400:
            for r in resp_stock_color.json():
                key = f"{r.get('estilo', '')}|{r.get('modelo', '')}"
                if key not in color_detail:
                    color_detail[key] = []
                color_detail[key].append({
                    "color": r.get("color", "") or "Sin color",
                    "t1": int(r.get("terex1_stock", 0) or 0),
                    "t2": int(r.get("terex2_stock", 0) or 0),
                    "total": int(r.get("total_stock", 0) or 0),
                })

        stock_by_modelo = {}
        modelo_detail = {}
        if resp_stock_detail.status_code < 400:
            for r in resp_stock_detail.json():
                mod = r.get("modelo", "")
                est = r.get("estilo", "")
                t1 = int(r.get("terex1_stock", 0) or 0)
                t2 = int(r.get("terex2_stock", 0) or 0)
                total = int(r.get("total_stock", 0) or 0)
                if mod not in stock_by_modelo:
                    stock_by_modelo[mod] = {"modelo": mod, "t1": 0, "t2": 0, "total": 0}
                stock_by_modelo[mod]["t1"] += t1
                stock_by_modelo[mod]["t2"] += t2
                stock_by_modelo[mod]["total"] += total
                if mod not in modelo_detail:
                    modelo_detail[mod] = []
                modelo_detail[mod].append({"estilo": est, "t1": t1, "t2": t2, "total": total})
        stock_by_modelo_list = sorted(stock_by_modelo.values(), key=lambda x: x["total"], reverse=True)

        modelos = resp_modelos.json() if resp_modelos.status_code < 400 else []

        return templates.TemplateResponse(
            request=request,
            name="catalogo.html",
            context={
                "stock_by_estilo": stock_by_estilo,
                "stock_detail": stock_detail,
                "color_detail": color_detail,
                "stock_by_modelo": stock_by_modelo_list,
                "modelo_detail": modelo_detail,
                "estilo_ids": estilo_ids,
                "modelos": modelos,
            }
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return HTMLResponse(f"<h3>Error cargando catalogo</h3><p>{e}</p>", status_code=500)


@app.get("/catalogo/{estilo_id}", response_class=HTMLResponse)
async def catalogo_detalle(request: Request, estilo_id: int):
    """Product detail page – placeholder for future implementation."""
    # Fetch estilo name
    estilo_name = ""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/inventario_estilos",
                headers=HEADERS,
                params={"select": "id,nombre", "id": f"eq.{estilo_id}", "limit": "1"}
            )
            if resp.status_code < 400:
                rows = resp.json()
                if rows:
                    estilo_name = rows[0].get("nombre", "")
    except Exception:
        pass

    return templates.TemplateResponse(
        request=request,
        name="catalogo_detalle.html",
        context={"estilo_id": estilo_id, "estilo_name": estilo_name}
    )


@app.get("/api/images/{estilo_id}")
async def get_estilo_images(estilo_id: int):
    """Return estilo-level images, color-level images, and barcodes grouped by modelo|color."""
    result = {"estilo_images": [], "color_images": {}, "barcodes": {}}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            bucket_resp, uploads_resp, inv_resp = await asyncio.gather(
                client.post(
                    f"{SUPABASE_URL}/storage/v1/object/list/images_estilos",
                    headers=STORAGE_HEADERS,
                    json={"prefix": f"{estilo_id}/", "limit": 20}
                ),
                client.get(
                    f"{SUPABASE_URL}/rest/v1/image_uploads",
                    headers=HEADERS,
                    params={
                        "select": "public_url,color_id",
                        "estilo_id": f"eq.{estilo_id}",
                        "limit": "100",
                    }
                ),
                client.get(
                    f"{SUPABASE_URL}/rest/v1/inventario1",
                    headers={**HEADERS, "Range": "0-999"},
                    params={
                        "select": "barcode,color_id,modelo_id",
                        "estilo_id": f"eq.{estilo_id}",
                        "limit": "1000",
                    }
                ),
            )

            all_color_ids = set()
            all_modelo_ids = set()

            # Estilo bucket
            if bucket_resp.status_code < 400:
                for f in bucket_resp.json():
                    if f.get("name") and f.get("id"):
                        url = f"{SUPABASE_URL}/storage/v1/object/public/images_estilos/{estilo_id}/{f['name']}"
                        result["estilo_images"].append(url)

            # Group uploads by color_id
            by_color_id_imgs = {}
            if uploads_resp.status_code < 400:
                for img in uploads_resp.json():
                    cid = img.get("color_id")
                    if cid and img.get("public_url"):
                        all_color_ids.add(cid)
                        by_color_id_imgs.setdefault(cid, []).append(img["public_url"])

            # Group barcodes by (modelo_id, color_id)
            by_mc_barcodes = {}  # (modelo_id, color_id) -> [barcode, ...]
            if inv_resp.status_code < 400:
                for row in inv_resp.json():
                    cid = row.get("color_id")
                    mid = row.get("modelo_id")
                    bc = row.get("barcode")
                    if cid and mid and bc:
                        all_color_ids.add(cid)
                        all_modelo_ids.add(mid)
                        by_mc_barcodes.setdefault((mid, cid), []).append(str(bc))

            # Resolve color names
            color_names = {}
            if all_color_ids:
                cnames_resp = await client.get(
                    f"{SUPABASE_URL}/rest/v1/inventario_colores",
                    headers=HEADERS,
                    params={
                        "select": "id,color",
                        "id": f"in.({','.join(str(c) for c in all_color_ids)})",
                    }
                )
                if cnames_resp.status_code < 400:
                    for c in cnames_resp.json():
                        color_names[c["id"]] = c.get("color", "")

            # Resolve modelo names
            modelo_names = {}
            if all_modelo_ids:
                mnames_resp = await client.get(
                    f"{SUPABASE_URL}/rest/v1/inventario_modelos",
                    headers=HEADERS,
                    params={
                        "select": "id,modelo",
                        "id": f"in.({','.join(str(m) for m in all_modelo_ids)})",
                    }
                )
                if mnames_resp.status_code < 400:
                    for m in mnames_resp.json():
                        modelo_names[m["id"]] = m.get("modelo", "")

            # Build color_images by color name
            for cid, urls in by_color_id_imgs.items():
                name = color_names.get(cid, f"Color {cid}")
                result["color_images"][name] = urls

            # Build barcodes keyed by "modelo_name|color_name"
            for (mid, cid), barcodes in by_mc_barcodes.items():
                mname = modelo_names.get(mid, "")
                cname = color_names.get(cid, "")
                key = f"{mname}|{cname}"
                result["barcodes"][key] = barcodes

    except Exception as e:
        print(f"Error fetching images for estilo {estilo_id}: {e}", flush=True)

    return JSONResponse(result)


@app.get("/api/browse-modelo")
async def api_browse_modelo(modelo: str, days: int = 30):
    """Return estilo+color products for a given modelo with images and metrics."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp_analysis, resp_images, resp_estilos = await asyncio.gather(
                client.get(
                    f"{SUPABASE_URL}/rest/v1/rpc/get_order_analysis",
                    headers={**HEADERS, "Range": "0-9999"},
                    params={"days_back": days}
                ),
                client.get(
                    f"{SUPABASE_URL}/rest/v1/image_uploads",
                    headers={**HEADERS, "Range": "0-9999"},
                    params={"select": "estilo_id,color_id,public_url"}
                ),
                client.get(
                    f"{SUPABASE_URL}/rest/v1/inventario_estilos",
                    headers={**HEADERS, "Range": "0-9999"},
                    params={"select": "id,nombre"}
                ),
            )

        if resp_analysis.status_code >= 400:
            raise HTTPException(status_code=500, detail=f"RPC error: {resp_analysis.text}")

        all_rows = resp_analysis.json()

        # Build estilo name -> id map
        estilo_id_map = {}
        for e in (resp_estilos.json() if resp_estilos.status_code < 400 else []):
            estilo_id_map[e["nombre"]] = e["id"]

        # Build image lookup: images_by_estilo[estilo_id][color_id] = url
        images_by_estilo = {}
        if resp_images.status_code < 400:
            for img in resp_images.json():
                eid = img.get("estilo_id")
                cid = img.get("color_id")
                url = img.get("public_url", "")
                if eid and url:
                    if eid not in images_by_estilo:
                        images_by_estilo[eid] = {}
                    if cid not in images_by_estilo[eid]:
                        images_by_estilo[eid][cid] = url

        # Resolve color names to color_ids for image matching
        async with httpx.AsyncClient(timeout=15) as client:
            resp_colors = await client.get(
                f"{SUPABASE_URL}/rest/v1/inventario_colores",
                headers={**HEADERS, "Range": "0-9999"},
                params={"select": "id,color", "order": "color.asc"}
            )
        color_name_to_id = {}
        if resp_colors.status_code < 400:
            for c in resp_colors.json():
                color_name_to_id[c["color"].strip().upper()] = c["id"]

        # Filter rows for the requested modelo
        filtered = [
            r for r in all_rows
            if (r.get("modelo") or "").strip().upper() == modelo.strip().upper()
            and (float(r.get("stock_total", 0) or 0) > 0
                 or float(r.get("sold_total", 0) or 0) > 0)
        ]

        # Build product list
        products = []
        for r in filtered:
            est = r.get("estilo", "") or "Sin estilo"
            color = r.get("color", "") or "Sin color"
            stock = int(float(r.get("stock_total", 0) or 0))
            sold = int(float(r.get("sold_total", 0) or 0))
            rev = float(r.get("revenue_total", 0) or 0)
            avg_daily = float(r.get("avg_daily_sales", 0) or 0)
            doi = r.get("days_of_inventory")
            doi = round(float(doi), 1) if doi is not None else None

            # Resolve image
            eid = estilo_id_map.get(est)
            cid = color_name_to_id.get(color.strip().upper())
            image_url = ""
            has_image = False
            if eid and cid and eid in images_by_estilo:
                image_url = images_by_estilo[eid].get(cid, "")
            if not image_url and eid and eid in images_by_estilo:
                imgs = images_by_estilo[eid]
                if imgs:
                    image_url = next(iter(imgs.values()), "")
            if image_url:
                has_image = True

            products.append({
                "estilo": est,
                "color": color,
                "stock": stock,
                "sold": sold,
                "revenue": round(rev),
                "avg_daily": round(avg_daily, 1),
                "doi": doi,
                "image_url": image_url,
                "has_image": has_image,
            })

        # Sort: items with images first, then by sold desc
        products.sort(key=lambda p: (-int(p["has_image"]), -p["sold"]))

        return JSONResponse({"products": products, "modelo": modelo, "count": len(products)})

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
