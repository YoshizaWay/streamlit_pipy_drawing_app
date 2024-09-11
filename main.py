import streamlit as st
from streamlit_drawable_canvas import st_canvas
import numpy as np
import json
import time

# サイドバーでパラメータを指定
stroke_width = st.sidebar.slider("Stroke width: ", 1, 25, 3)
stroke_color = st.sidebar.color_picker("Stroke color hex: ", "#000000")
bg_color = st.sidebar.color_picker("Background color hex: ", "#FFFFFF")

# JSONデータの読み込み
with open("shape_data.json") as f:
    shape_data = json.load(f)

# セッションステートの初期化
if "objects" not in st.session_state:
    st.session_state["objects"] = []  # 描画オブジェクトを保持する
if "transformation_steps" not in st.session_state:
    st.session_state["transformation_steps"] = []  # 変形の段階を保存
if "step_index" not in st.session_state:
    st.session_state["step_index"] = 0  # 現在のステップのインデックス
if "is_transforming" not in st.session_state:
    st.session_state["is_transforming"] = False  # 変形が進行中かどうかを保持

# 2つの点の間の距離を線形補間
def interpolate_points(points1, points2, steps):
    return [(1 - t) * np.array(points1) + t * np.array(points2) for t in np.linspace(0, 1, steps)]

# 描画された図形とJSON図形を10段階で変化させる
def generate_transformation_steps(drawn_shape, json_shape, steps=10):
    interpolated_shapes = []
    
    for i in range(steps):
        # 線形補間を行う
        interpolated_shape = []
        for p1, p2 in zip(drawn_shape, json_shape):
            interpolated_point = interpolate_points(p1, p2, steps)[i]
            interpolated_shape.append(interpolated_point)
        interpolated_shapes.append(interpolated_shape)
    
    return interpolated_shapes

# JSONデータのスケーリングを行う関数
def scale_json_shape(json_data, drawn_start, drawn_end):
    if len(json_data) == 0:
        return []

    # JSONデータの始点と終点を取得
    json_start = np.array(json_data[0][1:3])  # JSONの始点
    json_end = np.array(json_data[-1][-2:])   # JSONの終点

    # スケールの計算
    json_length = np.linalg.norm(json_end - json_start)
    drawn_length = np.linalg.norm(drawn_end - drawn_start)

    scale_factor = drawn_length / json_length

    # JSONデータのスケーリング
    scaled_json_shape = []
    for command in json_data:
        if command[0] == "M" or command[0] == "L":
            point = np.array([command[1], command[2]])
            scaled_point = (point - json_start) * scale_factor + drawn_start
            scaled_json_shape.append(scaled_point.tolist())
    
    return scaled_json_shape

# キャンバスの作成
canvas_result = st_canvas(
    stroke_width=stroke_width,
    stroke_color=stroke_color,
    background_color=bg_color,
    update_streamlit=True,
    height=400,
    width=600,
    drawing_mode="freedraw",
    key="canvas", 
    initial_drawing={"objects": st.session_state["objects"]} if st.session_state["objects"] else None  # セッションステートのオブジェクトを反映
)

# 描画の更新処理
if canvas_result.json_data is not None and not st.session_state["is_transforming"]:
    objects = canvas_result.json_data['objects']
    
    for obj in objects:
        if obj['type'] == 'path':  # フリーハンドのパスを取得
            path_data = obj['path']

            if len(path_data) == 0:
                continue

            # x, y 座標を抽出
            path = np.array([[p[1], p[2]] for p in path_data if len(p) == 3])

            # 最初と最後の点を取得
            start_point = path[0]
            end_point = path[-1]

            # JSONから読み込んだ形状をスケーリング
            scaled_json_shape = scale_json_shape(shape_data, start_point, end_point)

            # スケーリングした図形のプロット数を描画した図形のプロット数に合わせる
            drawn_shape = path.tolist()
            if len(drawn_shape) > len(scaled_json_shape):
                drawn_shape = drawn_shape[:len(scaled_json_shape)]

            # 変形の10段階を生成してセッションステートに保存
            st.session_state["transformation_steps"] = generate_transformation_steps(drawn_shape, scaled_json_shape)
            st.session_state["step_index"] = 0  # 初期化
            st.session_state["is_transforming"] = True  # 変形を開始

# 変形の段階的表示
if st.session_state["is_transforming"]:
    current_step = st.session_state["step_index"]
    step_shape = st.session_state["transformation_steps"][current_step]

    # 描画オブジェクトを更新
    new_objects = []
    for point in step_shape:
        new_objects.append({
            "type": "line",
            "x1": point[0],
            "y1": point[1],
            "x2": point[0],
            "y2": point[1],
            "stroke": stroke_color,
            "strokeWidth": stroke_width,
        })
    st.session_state["objects"] = new_objects  # セッションステートに保存

    # 次のステップに進む
    st.session_state["step_index"] += 1
    if st.session_state["step_index"] >= len(st.session_state["transformation_steps"]):
        st.session_state["is_transforming"] = False  # 変形終了

    # 0.2秒後に次のステップを描画する
    time.sleep(0.2)
    st.rerun()

# セッションステートの中身をデバッグ用に表示
st.write("Current Step:", st.session_state["step_index"])
st.write("Session State Objects:", st.session_state["objects"])

# セッションステートに保存されているオブジェクトをキャンバスに反映させるために再描画
if st.session_state["objects"]:
    st_canvas(
        stroke_width=stroke_width,
        stroke_color=stroke_color,
        background_color=bg_color,
        update_streamlit=True,
        height=400,
        width=600,
        drawing_mode="freedraw",
        key="canvas_final",  # 新しいキャンバスを追加してセッションステートの内容を反映
        initial_drawing={"objects": st.session_state["objects"]}
    )
