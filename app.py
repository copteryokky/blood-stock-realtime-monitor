# ===== DETAIL =====
if not selected:
    st.info("กดเลือกรายละเอียดที่กรุ๊ปโลหิตด้านบน เพื่อดูสต็อกตามประเภทผลิตภัณฑ์และทำรายการเบิก/นำเข้า")
else:
    st.subheader(f"รายละเอียดกรุ๊ป {selected}")

    total_selected = next(d for d in overview if d["blood_type"] == selected)["total"]
    dist_selected = normalize_products(get_stock_by_blood(selected))

    st_html(bag_svg_with_distribution(selected, int(total_selected), dist_selected), height=270, scrolling=False)

    # --- ตาราง+กราฟ (แก้สีด้วยคอลัมน์ ไม่ใช้ alt.condition) ---
    df = pd.DataFrame([{"product_type": k, "units": v} for k, v in dist_selected.items()])
    # จัดลำดับแกน X
    df = df.set_index("product_type").loc[ALL_PRODUCTS_UI].reset_index()

    # สีตามไฟจราจร
    def color_by_rule(u: int) -> str:
        if u <= CRITICAL_MAX:
            return "#ef4444"  # แดง
        elif u <= YELLOW_MAX:
            return "#f59e0b"  # เหลือง
        return "#22c55e"      # เขียว

    df["color"] = df["units"].apply(color_by_rule)

    # ขอบเขตแกน Y ให้พอดีกับค่าจริง (อย่างน้อย BAG_MAX)
    y_max = max(int(df["units"].max()), BAG_MAX)

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("product_type:N", title="ประเภทผลิตภัณฑ์ (LPRC, PRC, FFP, Cryo=รวม, PC)"),
            y=alt.Y("units:Q", title="จำนวนหน่วย (unit)", scale=alt.Scale(domainMin=0, domainMax=y_max)),
            color=alt.Color("color:N", scale=None, legend=None),
            tooltip=["product_type", "units"],
        )
        .properties(height=340)
    )
    st.altair_chart(chart, use_container_width=True)

    st.dataframe(df.drop(columns=["color"]), use_container_width=True, hide_index=True)

    # ===== Update Mode =====
    if admin_mode and pin_ok:
        st.markdown("#### ปรับปรุงคลัง")
        c1, c2, c3 = st.columns([1,1,2])
        with c1:
            # Cryo คือยอดรวม ไม่ให้แก้โดยตรง
            product = st.selectbox("ประเภทผลิตภัณฑ์", ["LPRC", "PRC", "FFP", "PC"])
        with c2:
            qty = int(st.number_input("จำนวน (หน่วย)", min_value=1, max_value=1000, value=1, step=1))
        with c3:
            note = st.text_input("หมายเหตุ", placeholder="เหตุผลการทำรายการ เช่น นำเข้า/เบิกให้ผู้ป่วย/ทดแทนการหมดอายุ")

        current_total = int(total_selected)
        current_by_product = int(dist_selected.get(product, 0))

        b1, b2 = st.columns(2)
        with b1:
            if st.button("➕ นำเข้าเข้าคลัง", use_container_width=True):
                space = max(0, BAG_MAX - min(current_total, BAG_MAX))   # จำกัดรวมไม่เกิน 20
                add = min(qty, space)
                if add <= 0:
                    st.warning("เต็มคลังแล้ว (20/20) – ไม่สามารถนำเข้าเพิ่มได้")
                else:
                    adjust_stock(selected, product, add, actor="admin", note=note or "inbound")
                    if add < qty:
                        st.info(f"นำเข้าได้เพียง {add} หน่วย (จำกัดเต็มคลัง 20)")
                    st.toast("บันทึกการนำเข้าแล้ว", icon="✅")
                    st.rerun()

        with b2:
            if st.button("➖ เบิกออกจากคลัง", use_container_width=True):
                take = min(qty, current_by_product)  # ไม่ให้ติดลบ
                if take <= 0:
                    st.warning(f"ไม่มี {product} ในกรุ๊ป {selected} เพียงพอสำหรับการเบิก")
                else:
                    adjust_stock(selected, product, -take, actor="admin", note=note or "outbound")
                    if take < qty:
                        st.info(f"ทำการเบิกได้เพียง {take} หน่วย (ตามยอดคงเหลือ)")
                    st.toast("บันทึกการเบิกออกแล้ว", icon="✅")
                    st.rerun()
