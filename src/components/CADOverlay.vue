<template>
  <!-- CAD红线上传叠加组件（用于基地范围确认） -->

  <!-- 隐藏的文件输入（通过按钮触发） -->
  <input
    ref="fileInput"
    type="file"
    accept=".dxf,.pdf"
    @change="handleFileUpload"
    :disabled="state.isLoading"
    style="display: none;"
  />

  <!-- CAD叠加调整面板 -->
  <div v-if="state.isLoaded && selectMode" class="cad-overlay-panel" :style="overlayPanelStyle">
    <canvas
      ref="cadCanvas"
      class="cad-canvas"
      :width="state.canvasWidth"
      :height="state.canvasHeight"
      @mousedown="handleMouseDown"
      @wheel="handleWheel"
      @click="handleCanvasClick"
    />

    <div class="cad-toolbar">
      <div class="toolbar-row">
        <button @click="scale(0.9)" title="缩小">➖</button>
        <span class="scale-value">{{ (state.scale * 100).toFixed(0) }}%</span>
        <button @click="scale(1.1)" title="放大">➕</button>
      </div>

      <div class="toolbar-row">
        <label class="opacity-label">
          旋转角度
          <div style="display: flex; align-items: center; gap: 8px;">
            <input
              type="range"
              v-model.number="state.rotation"
              min="0"
              max="360"
              step="1"
              style="flex: 1;"
            />
            <span style="color: #fff; font-size: 12px; min-width: 45px;">{{ state.rotation.toFixed(0) }}°</span>
          </div>
        </label>
      </div>


      <div class="toolbar-actions">
        <button 
          class="btn-confirm" 
          @click="confirmPosition"
        >
          ✓ 确认红线范围{{ state.selectedIndices.size > 0 ? ` (${state.selectedIndices.size})` : '' }}
        </button>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick, onMounted, onUnmounted } from 'vue';

const props = defineProps({
  mapInstance: { type: Object, required: true },
  amap: { type: Object, required: true }, // AMap
  selectMode: { type: Boolean, default: false },
  captureRect: { type: Object, default: null },
  detectedContours: { type: Array, default: () => [] }, // 已识别的轮廓（用于匹配）
  autoMatchEnabled: { type: Boolean, default: false } // 是否启用自动匹配
});

const emit = defineEmits(['cad-confirmed', 'cad-cleared', 'cad-loaded']);

const cadCanvas = ref(null);
const fileInput = ref(null);

const state = reactive({
  isLoading: false,
  isLoaded: false,
  error: null,

  polygons: [], // 归一化坐标0-1
  selectedIndices: new Set(), // 选中的轮廓索引（不默认选中）
  
  cadBounds: null, // CAD文件的原始边界（用于保持宽高比）
  cadAspectRatio: 1, // CAD文件的宽高比

  canvasWidth: 600,
  canvasHeight: 600,
  // CAD 在画布内的绘制区域（保持宽高比，居中），与 canvas 尺寸可不同
  cadDrawWidth: 600,
  cadDrawHeight: 600,
  cadDrawOffsetX: 0,
  cadDrawOffsetY: 0,

  offsetX: 0,
  offsetY: 0,
  scale: 1,
  rotation: 0, // 旋转角度（度）
  opacity: 0.7,

  isDragging: false,
  dragStartX: 0,
  dragStartY: 0,
  dragStartOffsetX: 0,
  dragStartOffsetY: 0
});

const overlayPanelStyle = computed(() => {
  if (!props.captureRect) {
    return {
      position: 'absolute',
      left: '50%',
      top: '50%',
      transform: 'translate(-50%, -50%)'
    };
  }

  // 与识别紫色轮廓时的预览范围保持一致，使用完整的 captureRect 尺寸
  const displayWidth = props.captureRect.width;
  const displayHeight = props.captureRect.height;

  return {
    position: 'absolute',
    left: `${props.captureRect.left}px`,
    top: `${props.captureRect.top}px`,
    width: `${displayWidth}px`,
    height: `${displayHeight}px`
  };
});

async function handleFileUpload(event) {
  const file = event.target.files?.[0];
  if (!file) return;

  state.isLoading = true;
  state.error = null;

  try {
    const base64 = await readFileAsBase64(file);
    const response = await fetch('http://127.0.0.1:5000/parse-cad', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        file: base64,
        filename: file.name
      })
    });

    const result = await response.json();
    if (!result.ok) throw new Error(result.error || '解析失败');

    state.polygons = result.polygons || [];
    state.selectedIndices = new Set(); // 不默认选中，让用户自己选择
    
    // 保存CAD文件的原始边界和宽高比
    if (result.bounds) {
      state.cadBounds = result.bounds;
      const [min_x, min_y, max_x, max_y] = result.bounds;
      const cadWidth = max_x - min_x;
      const cadHeight = max_y - min_y;
      state.cadAspectRatio = cadHeight > 0 ? cadWidth / cadHeight : 1;
    } else {
      state.cadAspectRatio = 1;
    }

    if (props.captureRect) {
      const rectWidth = props.captureRect.width;
      const rectHeight = props.captureRect.height;
      // 画布 = 完整预览范围，避免拖拽时轮廓超出被裁剪
      state.canvasWidth = Math.max(1, Math.round(rectWidth));
      state.canvasHeight = Math.max(1, Math.round(rectHeight));
      // CAD 绘制区域保持宽高比，居中于画布内（无畸变）
      const rectAspectRatio = rectHeight > 0 ? rectWidth / rectHeight : 1;
      if (state.cadAspectRatio > rectAspectRatio) {
        state.cadDrawWidth = rectWidth;
        state.cadDrawHeight = Math.max(1, Math.round(rectWidth / state.cadAspectRatio));
      } else {
        state.cadDrawWidth = Math.max(1, Math.round(rectHeight * state.cadAspectRatio));
        state.cadDrawHeight = rectHeight;
      }
      state.cadDrawOffsetX = (state.canvasWidth - state.cadDrawWidth) / 2;
      state.cadDrawOffsetY = (state.canvasHeight - state.cadDrawHeight) / 2;
    }

    state.isLoaded = true;
    
    // 通知父组件CAD已加载
    emit('cad-loaded');

    nextTick(() => {
      draw();
    });
  } catch (e) {
    console.error('CAD解析失败:', e);
    state.error = e?.message || String(e);
  } finally {
    state.isLoading = false;
    event.target.value = '';
  }
}

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error('文件读取失败'));
    reader.readAsDataURL(file);
  });
}

// 进入 CAD 模式时自动弹出系统文件选择框
function openFileDialog() {
  if (fileInput.value && !state.isLoading) {
    fileInput.value.click();
  }
}

// 触发文件上传（供父组件调用）
function triggerFileUpload() {
  console.log('触发文件上传，fileInput:', fileInput.value);
  if (fileInput.value && !state.isLoading) {
    fileInput.value.click();
  } else {
    console.warn('fileInput未准备好或正在加载中');
  }
}

// 暴露方法供父组件调用
defineExpose({
  triggerFileUpload
});






function draw() {
  const canvas = cadCanvas.value;
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const width = canvas.width;
  const height = canvas.height;
  const dw = state.cadDrawWidth;
  const dh = state.cadDrawHeight;
  const dx = state.cadDrawOffsetX;
  const dy = state.cadDrawOffsetY;
  ctx.clearRect(0, 0, width, height);

  ctx.save();
  ctx.globalAlpha = state.opacity;

  // 以 CAD 绘制区域中心为基准做平移+缩放+旋转（保持宽高比无畸变）
  const centerX = dx + dw / 2 + state.offsetX;
  const centerY = dy + dh / 2 + state.offsetY;
  ctx.translate(centerX, centerY);
  ctx.rotate((state.rotation * Math.PI) / 180);
  ctx.scale(state.scale, state.scale);
  ctx.translate(-(dx + dw / 2), -(dy + dh / 2));

  // 归一化坐标映射到 CAD 绘制区域（保持宽高比）
  state.polygons.forEach((poly, index) => {
    const isSelected = state.selectedIndices.has(index);
    const coords = poly.coordinates;
    if (!coords || coords.length < 3) return;

    const canvasCoords = coords.map(([nx, ny]) => ({
      x: dx + nx * dw,
      y: dy + ny * dh
    }));

    ctx.fillStyle = isSelected ? 'rgba(255, 0, 0, 0.25)' : 'rgba(120, 120, 120, 0.12)';
    ctx.strokeStyle = '#ff0000';  // 改为始终红色
    ctx.lineWidth = 3;            // 改为始终2像素（或3）

    ctx.beginPath();
    canvasCoords.forEach((p, i) => {
      ctx[i === 0 ? 'moveTo' : 'lineTo'](p.x, p.y);
    });
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  });

  ctx.restore();
}

let dragStartPos = null;
const DRAG_THRESHOLD = 5; // 拖拽阈值（像素）

function handleMouseDown(event) {
  dragStartPos = {
    x: event.clientX,
    y: event.clientY,
    offsetX: state.offsetX,
    offsetY: state.offsetY
  };
  
  document.addEventListener('mousemove', onDrag);
  document.addEventListener('mouseup', stopDrag);
}

function startDrag(event) {
  state.isDragging = true;
  state.dragStartX = event.clientX;
  state.dragStartY = event.clientY;
  state.dragStartOffsetX = state.offsetX;
  state.dragStartOffsetY = state.offsetY;
}

function onDrag(event) {
  if (!dragStartPos) return;
  
  const dx = event.clientX - dragStartPos.x;
  const dy = event.clientY - dragStartPos.y;
  const distance = Math.sqrt(dx * dx + dy * dy);
  
  // 如果移动距离超过阈值，开始拖拽
  if (distance > DRAG_THRESHOLD && !state.isDragging) {
    startDrag(event);
  }
  
  if (state.isDragging) {
    state.offsetX = dragStartPos.offsetX + dx;
    state.offsetY = dragStartPos.offsetY + dy;
    draw();
  }
}

function stopDrag(event) {
  const wasDragging = state.isDragging;
  state.isDragging = false;
  dragStartPos = null;
  
  document.removeEventListener('mousemove', onDrag);
  document.removeEventListener('mouseup', stopDrag);
  
  // 如果没有拖拽，可能是点击事件
  if (!wasDragging && event) {
    handleCanvasClick(event);
  }
}

// 判断点是否在多边形内（使用射线法）
function isPointInPolygon(x, y, coords) {
  let inside = false;
  for (let i = 0, j = coords.length - 1; i < coords.length; j = i++) {
    const xi = coords[i].x, yi = coords[i].y;
    const xj = coords[j].x, yj = coords[j].y;
    if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) {
      inside = !inside;
    }
  }
  return inside;
}

// 处理Canvas点击事件（选择轮廓）
function handleCanvasClick(event) {
  if (state.isDragging) return; // 如果正在拖拽，不处理点击
  
  const canvas = cadCanvas.value;
  if (!canvas) return;
  
  const rect = canvas.getBoundingClientRect();
  const clickX = event.clientX - rect.left;
  const clickY = event.clientY - rect.top;
  
  const dw = state.cadDrawWidth;
  const dh = state.cadDrawHeight;
  const dx = state.cadDrawOffsetX;
  const dy = state.cadDrawOffsetY;
  const centerX = dx + dw / 2 + state.offsetX;
  const centerY = dy + dh / 2 + state.offsetY;
  
  // 将点击坐标反向变换到 CAD 绘制区坐标系（与 draw() 的变换相反）
  const rotationRad = -(state.rotation * Math.PI) / 180;
  const cos = Math.cos(rotationRad);
  const sin = Math.sin(rotationRad);
  let invX = (clickX - centerX) * cos - (clickY - centerY) * sin;
  let invY = (clickX - centerX) * sin + (clickY - centerY) * cos;
  invX = invX / state.scale + dx + dw / 2;
  invY = invY / state.scale + dy + dh / 2;
  
  // 检查点击了哪个轮廓（从后往前，后绘制的在上层）
  let clickedIndex = -1;
  for (let i = state.polygons.length - 1; i >= 0; i--) {
    const poly = state.polygons[i];
    const coords = poly.coordinates;
    if (!coords || coords.length < 3) continue;
    
    const canvasCoords = coords.map(([px, py]) => ({
      x: dx + px * dw,
      y: dy + py * dh
    }));
    
    if (isPointInPolygon(invX, invY, canvasCoords)) {
      clickedIndex = i;
      break;
    }
  }
  
  if (clickedIndex === -1) return;
  
  // 根据按键状态处理选择
  if (event.shiftKey) {
    // Shift+点击：添加选中
    state.selectedIndices.add(clickedIndex);
  } else if (event.ctrlKey || event.metaKey) {
    // Ctrl+点击：移除选中
    state.selectedIndices.delete(clickedIndex);
  } else {
    // 普通点击：切换选中状态
    if (state.selectedIndices.has(clickedIndex)) {
      state.selectedIndices.delete(clickedIndex);
    } else {
      state.selectedIndices.add(clickedIndex);
    }
  }
  
  draw();
}

function handleWheel(event) {
  event.preventDefault();
  const factor = event.deltaY > 0 ? 0.95 : 1.05;
  scale(factor);
}

function scale(factor) {

  const adjustedFactor = factor > 1 ? 1.01 : 0.99;
  state.scale = Math.max(0.1, Math.min(10, state.scale * adjustedFactor));
  draw();
}

function rotate(degrees) {
  state.rotation = (state.rotation + degrees) % 360;
  if (state.rotation < 0) state.rotation += 360;
  draw();
}


function confirmPosition() {
  const map = props.mapInstance;
  const AMap = props.amap;
  if (!map || !AMap) return;

  const canvas = cadCanvas.value;
  if (!canvas) return;


  const width = canvas.width;
  const height = canvas.height;
  const dw = state.cadDrawWidth;
  const dh = state.cadDrawHeight;
  const dx = state.cadDrawOffsetX;
  const dy = state.cadDrawOffsetY;
  
  // 如果没有选中，使用所有轮廓；否则使用选中的
  const polygonsToUse = state.selectedIndices.size === 0 
    ? state.polygons 
    : state.polygons.filter((_, index) => state.selectedIndices.has(index));

  const geoPolygons = polygonsToUse.map((poly) => {
    const transformedPixelCoords = poly.coordinates.map(([nx, ny]) => {
      const centerX = dx + dw / 2 + state.offsetX;
      const centerY = dy + dh / 2 + state.offsetY;
      let x = dx + nx * dw;
      let y = dy + ny * dh;
      const px = (x - centerX) * state.scale;
      const py = (y - centerY) * state.scale;
      const rotationRad = (state.rotation * Math.PI) / 180;
      const cos = Math.cos(rotationRad);
      const sin = Math.sin(rotationRad);
      x = centerX + px * cos - py * sin;
      y = centerY + px * sin + py * cos;
      return { x, y };
    });

    const canvasDisplayLeft = props.captureRect?.left ?? 0;
    const canvasDisplayTop = props.captureRect?.top ?? 0;

    const lngLatCoords = transformedPixelCoords.map(({ x, y }) => {
      const pixel = new AMap.Pixel(canvasDisplayLeft + x, canvasDisplayTop + y);
      const lngLat = map.containerToLngLat(pixel);
      return [lngLat.lng, lngLat.lat];
    });

    return {
      type: poly.type || 'redline',
      pixelCoords: transformedPixelCoords,
      lngLatCoords
    };
  });

  emit('cad-confirmed', {
    polygons: geoPolygons,
    transform: {
      offsetX: state.offsetX,
      offsetY: state.offsetY,
      scale: state.scale,
      rotation: state.rotation
    }
  });
}


watch(
  () => state.rotation,
  () => draw()
);

// 监听自动匹配启用状态和CAD加载状态
watch(
  () => [props.autoMatchEnabled, state.isLoaded],
  ([enabled, loaded]) => {
    if (enabled && loaded && props.detectedContours && props.detectedContours.length > 0) {
      // 延迟一下确保轮廓数据已更新
      nextTick(() => {
        console.log('触发自动匹配，紫色轮廓已确认，CAD已加载');
        autoMatchWithDetectedContours();
      });
    }
  }
);

// 监听检测到的轮廓变化
watch(
  () => props.detectedContours,
  (newContours) => {
    if (props.autoMatchEnabled && state.isLoaded && newContours && newContours.length > 0) {
      nextTick(() => {
        console.log('检测到轮廓变化，触发自动匹配');
        autoMatchWithDetectedContours();
      });
    }
  },
  { deep: true }
);

function autoMatchWithDetectedContours() {
  autoMatchWithDetectedContoursOptimized();
}

onUnmounted(() => {
  document.removeEventListener('mousemove', onDrag);
  document.removeEventListener('mouseup', stopDrag);
  dragStartPos = null;
});


// CADOverlay.vue - 优化后的匹配算法部分

// ============ 核心优化：基于SVD的鲁棒形状匹配 ============

/**
 * 使用Kabsch算法（SVD）计算最佳刚体变换
 * 比PCA更稳定，直接给出旋转矩阵和平移向量
 */
function kabschAlgorithm(sourcePoints, targetPoints) {
  const n = sourcePoints.length;
  if (n !== targetPoints.length || n < 3) {
    throw new Error('点集数量不匹配或不足');
  }

  // 1. 计算质心
  const sourceCentroid = calculateCentroid(sourcePoints);
  const targetCentroid = calculateCentroid(targetPoints);

  // 2. 中心化点集
  const sourceCentered = sourcePoints.map(p => [
    p[0] - sourceCentroid[0],
    p[1] - sourceCentroid[1]
  ]);
  const targetCentered = targetPoints.map(p => [
    p[0] - targetCentroid[0],
    p[1] - targetCentroid[1]
  ]);

  // 3. 构建协方差矩阵 H = P^T * Q
  // 对于2D情况，这是2x2矩阵
  let h00 = 0, h01 = 0, h10 = 0, h11 = 0;
  for (let i = 0; i < n; i++) {
    h00 += sourceCentered[i][0] * targetCentered[i][0];
    h01 += sourceCentered[i][0] * targetCentered[i][1];
    h10 += sourceCentered[i][1] * targetCentered[i][0];
    h11 += sourceCentered[i][1] * targetCentered[i][1];
  }

  // 4. SVD分解 H = U * Σ * V^T
  const { U, S, Vt } = svd2x2([[h00, h01], [h10, h11]]);

  // 5. 计算旋转矩阵 R = V * U^T
  let R = matrixMultiply(transpose(Vt), transpose(U));
  
  // 6. 处理反射情况（确保是正常旋转而非反射）
  const det = R[0][0] * R[1][1] - R[0][1] * R[1][0];
  if (det < 0) {
    // 如果是反射，翻转V的最后一列
    Vt[1][0] = -Vt[1][0];
    Vt[1][1] = -Vt[1][1];
    R = matrixMultiply(transpose(Vt), transpose(U));
  }

  // 7. 计算旋转角度
  const rotationAngle = Math.atan2(R[1][0], R[0][0]);

  // 8. 计算平移向量 t = targetCentroid - R * sourceCentroid
  const rotatedSourceCentroid = [
    R[0][0] * sourceCentroid[0] + R[0][1] * sourceCentroid[1],
    R[1][0] * sourceCentroid[0] + R[1][1] * sourceCentroid[1]
  ];
  const translation = [
    targetCentroid[0] - rotatedSourceCentroid[0],
    targetCentroid[1] - rotatedSourceCentroid[1]
  ];

  // 9. 计算缩放比例（基于点集包围盒或面积）
  const sourceScale = calculatePointCloudScale(sourcePoints);
  const targetScale = calculatePointCloudScale(targetPoints);
  const scale = targetScale / sourceScale;

  return {
    rotation: rotationAngle,
    translation: translation,
    scale: scale,
    rotationMatrix: R
  };
}

/**
 * 2x2矩阵的SVD分解（简化实现）
 * 对于更高精度需求，可以引入numeric.js等库
 */
function svd2x2(A) {
  // 使用Jacobi方法进行SVD分解
  const a = A[0][0], b = A[0][1], c = A[1][0], d = A[1][1];
  
  // 计算ATA的特征值
  const ata00 = a*a + c*c;
  const ata01 = a*b + c*d;
  const ata11 = b*b + d*d;
  
  // 特征值
  const trace = ata00 + ata11;
  const det = ata00 * ata11 - ata01 * ata01;
  const discriminant = Math.sqrt(trace*trace - 4*det);
  const s1 = Math.sqrt((trace + discriminant) / 2);
  const s2 = Math.sqrt((trace - discriminant) / 2);
  
  // 简化：使用atan2计算旋转角度
  const theta = 0.5 * Math.atan2(2*ata01, ata00 - ata11);
  
  const cos = Math.cos(theta);
  const sin = Math.sin(theta);
  
  const U = [[cos, -sin], [sin, cos]];
  const Vt = [[cos, sin], [-sin, cos]];
  const S = [s1, s2];
  
  return { U, S, Vt };
}

// ============ 高级优化：ICP迭代精化 ============

/**
 * ICP（迭代最近点）算法精化变换参数
 * 通过多次迭代找到最佳对齐
 */
function iterativeClosestPoint(sourcePoints, targetPoints, maxIterations = 20, tolerance = 0.001) {
  let currentSource = [...sourcePoints];
  let bestTransform = null;
  let minError = Infinity;
  
  for (let iter = 0; iter < maxIterations; iter++) {
    // 1. 找到最近点对应关系
    const correspondences = findClosestPoints(currentSource, targetPoints);
    
    // 2. 使用Kabsch计算当前迭代的变换
    const transform = kabschAlgorithm(
      correspondences.map(c => c.source),
      correspondences.map(c => c.target)
    );
    
    // 3. 应用变换到源点集
    currentSource = sourcePoints.map(p => transformPoint(p, transform));
    
    // 4. 计算误差
    const error = calculateAlignmentError(currentSource, targetPoints, correspondences);
    
    // 5. 保存最佳结果
    if (error < minError) {
      minError = error;
      bestTransform = transform;
    }
    
    // 6. 检查收敛
    if (error < tolerance || (iter > 0 && Math.abs(minError - error) < tolerance * 0.1)) {
      console.log(`ICP收敛于第${iter + 1}次迭代，误差: ${error.toFixed(4)}`);
      break;
    }
  }
  
  return bestTransform || kabschAlgorithm(sourcePoints, targetPoints);
}

/**
 * 为每个源点找到目标点集中的最近点
 */
function findClosestPoints(sourcePoints, targetPoints) {
  const correspondences = [];
  
  for (const s of sourcePoints) {
    let minDist = Infinity;
    let closest = null;
    
    for (const t of targetPoints) {
      const dist = Math.hypot(s[0] - t[0], s[1] - t[1]);
      if (dist < minDist) {
        minDist = dist;
        closest = t;
      }
    }
    
    if (closest) {
      correspondences.push({ source: s, target: closest, distance: minDist });
    }
  }
  
  return correspondences;
}

/**
 * 计算对齐误差（均方根误差）
 */
function calculateAlignmentError(sourcePoints, targetPoints, correspondences) {
  let totalError = 0;
  for (const c of correspondences) {
    totalError += c.distance * c.distance;
  }
  return Math.sqrt(totalError / correspondences.length);
}

// ============ 辅助函数 ============

function calculateCentroid(points) {
  const sum = points.reduce((acc, p) => [acc[0] + p[0], acc[1] + p[1]], [0, 0]);
  return [sum[0] / points.length, sum[1] / points.length];
}

function calculatePointCloudScale(points) {
  // 使用点云的均方根距离作为尺度度量
  const centroid = calculateCentroid(points);
  let sumSq = 0;
  for (const p of points) {
    sumSq += Math.hypot(p[0] - centroid[0], p[1] - centroid[1]);
  }
  return sumSq / points.length;
}

function transformPoint(point, transform) {
  const { rotationMatrix, translation, scale } = transform;
  // 缩放 -> 旋转 -> 平移
  const scaled = [point[0] * scale, point[1] * scale];
  const rotated = [
    rotationMatrix[0][0] * scaled[0] + rotationMatrix[0][1] * scaled[1],
    rotationMatrix[1][0] * scaled[0] + rotationMatrix[1][1] * scaled[1]
  ];
  return [rotated[0] + translation[0], rotated[1] + translation[1]];
}

function matrixMultiply(A, B) {
  return [
    [A[0][0]*B[0][0] + A[0][1]*B[1][0], A[0][0]*B[0][1] + A[0][1]*B[1][1]],
    [A[1][0]*B[0][0] + A[1][1]*B[1][0], A[1][0]*B[0][1] + A[1][1]*B[1][1]]
  ];
}

function transpose(M) {
  return [[M[0][0], M[1][0]], [M[0][1], M[1][1]]];
}

// ============ 优化后的自动匹配主函数 ============

function autoMatchWithDetectedContoursOptimized() {
  if (!props.detectedContours || props.detectedContours.length === 0) {
    console.warn('没有检测到的轮廓进行匹配');
    return;
  }
  if (state.polygons.length === 0) {
    console.warn('没有CAD轮廓进行匹配');
    return;
  }
  
  // 使用第一个选中的轮廓
  const targetContour = props.detectedContours[0];
  if (!targetContour || !targetContour.coords || targetContour.coords.length < 3) {
    console.warn('未找到有效的目标轮廓进行匹配');
    return;
  }
  
  console.log('开始优化后的自动匹配，目标轮廓点数:', targetContour.coords.length);
  
  // 使用第一个CAD多边形
  const cadPolygon = state.polygons[0];
  if (!cadPolygon || !cadPolygon.coordinates || cadPolygon.coordinates.length < 3) return;
  
  const dw = state.cadDrawWidth;
  const dh = state.cadDrawHeight;
  const dx = state.cadDrawOffsetX;
  const dy = state.cadDrawOffsetY;

  // 将CAD多边形转换为画布像素坐标
  const cadPixelCoords = cadPolygon.coordinates.map(([nx, ny]) => [
    dx + nx * dw,
    dy + ny * dh
  ]);
  
  // 目标轮廓像素坐标
  const targetPixelCoords = targetContour.coords.map(p => [p.x, p.y]);
  
  // ===== 关键优化：使用ICP迭代精化 =====
  // 步骤1：降采样以提高效率（如果点太多）
  const cadSampled = resamplePolygon(cadPixelCoords, 50); // 最多50个点
  const targetSampled = resamplePolygon(targetPixelCoords, 50);
  
  // 步骤2：使用Kabsch算法获得初始变换
  let transform = kabschAlgorithm(cadSampled, targetSampled);
  
  // 步骤3：使用ICP迭代精化（如果点集足够大）
  if (cadSampled.length >= 10 && targetSampled.length >= 10) {
    try {
      const refinedTransform = iterativeClosestPoint(cadSampled, targetSampled, 15, 0.5);
      // 验证ICP结果是否更好
      const initialError = evaluateTransform(cadSampled, targetSampled, transform);
      const refinedError = evaluateTransform(cadSampled, targetSampled, refinedTransform);
      
      if (refinedError < initialError * 0.9) { // 至少提升10%才采用
        transform = refinedTransform;
        console.log('采用ICP精化结果，误差降低:', ((initialError - refinedError) / initialError * 100).toFixed(1) + '%');
      }
    } catch (e) {
      console.warn('ICP精化失败，使用初始Kabsch结果:', e);
    }
  }
  
  // 步骤4：将变换结果应用到绘制参数
  applyTransformToState(transform, dx, dy, dw, dh);
  
  draw();
  
  console.log('优化后的自动匹配完成:', {
    rotation: (transform.rotation * 180 / Math.PI).toFixed(1) + '°',
    scale: transform.scale.toFixed(3),
    offset: `(${state.offsetX.toFixed(1)}, ${state.offsetY.toFixed(1)})`
  });
}

/**
 * 多边形重采样：保持形状特征的同时减少点数
 */
function resamplePolygon(points, targetCount) {
  if (points.length <= targetCount) return points;
  
  const result = [];
  const step = points.length / targetCount;
  
  for (let i = 0; i < targetCount; i++) {
    const idx = Math.floor(i * step) % points.length;
    result.push(points[idx]);
  }
  
  return result;
}

/**
 * 评估变换质量
 */
function evaluateTransform(sourcePoints, targetPoints, transform) {
  const transformed = sourcePoints.map(p => transformPoint(p, transform));
  let totalError = 0;
  for (let i = 0; i < transformed.length; i++) {
    // 找到最近的目标点
    let minDist = Infinity;
    for (const t of targetPoints) {
      const dist = Math.hypot(transformed[i][0] - t[0], transformed[i][1] - t[1]);
      minDist = Math.min(minDist, dist);
    }
    totalError += minDist;
  }
  return totalError / transformed.length;
}

/**
 * 将数学变换应用到Vue状态
 */
function applyTransformToState(transform, dx, dy, dw, dh) {
  const { rotation, translation, scale } = transform;
  
  // 计算旋转角度（度）
  let rotationDeg = (rotation * 180 / Math.PI) % 360;
  if (rotationDeg < 0) rotationDeg += 360;
  state.rotation = rotationDeg;
  
  // 计算缩放（相对于当前绘制区域）
  state.scale = scale;
  
  // 计算偏移量（相对于画布中心）
  const centerX = dx + dw / 2;
  const centerY = dy + dh / 2;
  
  // 平移量需要补偿旋转中心的影响
  state.offsetX = translation[0];
  state.offsetY = translation[1];
}


</script>

<style scoped>
/* 上传界面样式已移除，改为通过按钮触发 */

.cad-overlay-panel {
  pointer-events: auto;
  z-index: 1002;
}

.cad-canvas {
  display: block;
  cursor: move;
  background: transparent;
}

.cad-toolbar {
  position: absolute;
  right: 200px;
  top: 80px;
  background: rgba(0, 0, 0, 0.85);
  border-radius: 8px;
  padding: 10px;
  width: 150px;
}

.toolbar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.toolbar-row button {
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 6px;
  background: #444;
  color: #fff;
  cursor: pointer;
  font-size: 16px;
}

.toolbar-row button:hover {
  background: #555;
}

.scale-value {
  color: #fff;
  font-size: 12px;
  min-width: 60px;
  text-align: center;
}

.opacity-label {
  color: #fff;
  font-size: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.opacity-label input {
  width: 100%;
}

.toolbar-actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.toolbar-actions button {
  padding: 8px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
}



.btn-confirm {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  color: #fff;
  font-weight: 700;
}

.btn-confirm:disabled {
  background: #555;
  opacity: 0.5;
  cursor: not-allowed;
}

.cad-hint {
  position: absolute;
  left: 50%;
  bottom: 12px;
  transform: translateX(-50%);
  color: #fff;
  font-size: 12px;
  background: rgba(0, 0, 0, 0.6);
  padding: 6px 10px;
  border-radius: 6px;
}
</style>

