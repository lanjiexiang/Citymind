<template>
<!-- CAD结果调整面板 -->
  <input
    ref="fileInput"
    type="file"
    accept=".dxf,.pdf"
    @change="handleFileUpload"
    :disabled="state.isLoading"
    style="display: none;"
  />
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


// 核心常量定义
const props = defineProps({
  mapInstance: { type: Object, required: true },     
  amap: { type: Object, required: true },             
  selectMode: { type: Boolean, default: false },     
  captureRect: { type: Object, default: null },       
  detectedContours: { type: Array, default: () => [] }, 
  autoMatchEnabled: { type: Boolean, default: false } 
});
const emit = defineEmits(['cad-confirmed', 'cad-cleared', 'cad-loaded']);
const cadCanvas = ref(null);   
const fileInput = ref(null);    
const state = reactive({
  isLoading: false,          
  isLoaded: false,           
  error: null,               
  polygons: [],              
  selectedIndices: new Set(), 
  cadBounds: null,          
  cadAspectRatio: 1,          
  canvasWidth: 600,           
  canvasHeight: 600,          
  cadDrawWidth: 600,          
  cadDrawHeight: 600,         
  cadDrawOffsetX: 0,          
  cadDrawOffsetY: 0,          
  offsetX: 0,               
  offsetY: 0,                 
  scale: 0.96,                   
  rotation: 0,             
  opacity: 0.7,            
  isDragging: false,         
  dragStartX: 0,             
  dragStartY: 0,              
  dragStartOffsetX: 0,        
  dragStartOffsetY: 0        
});
let dragStartPos = null;     
const DRAG_THRESHOLD = 5;    


//computed属性定义
const overlayPanelStyle = computed(() => {
  if (!props.captureRect) {
    return {
      position: 'absolute',
      left: '50%',
      top: '50%',
      transform: 'translate(-50%, -50%)'
    };
  }
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



//处理CAD文件上传
async function handleFileUpload(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  state.isLoading = true;
  state.error = null;

  try {
    // 读取文件为Base64格式
    const base64 = await readFileAsBase64(file);
    
    // 调用后端CAD解析服务
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
    state.selectedIndices = new Set(); 
    
    // 计算并保存CAD原始边界和宽高比，用于后续保持比例显示
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
      state.canvasWidth = Math.max(1, Math.round(rectWidth));
      state.canvasHeight = Math.max(1, Math.round(rectHeight));
      
      // 计算CAD绘制区域
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

function openFileDialog() {
  if (fileInput.value && !state.isLoading) {
    fileInput.value.click();
  }
}

function triggerFileUpload() {
  console.log('触发文件上传，fileInput:', fileInput.value);
  if (fileInput.value && !state.isLoading) {
    fileInput.value.click();
  } else {
    console.warn('fileInput未准备好或正在加载中');
  }
}

defineExpose({
  triggerFileUpload
});



//绘制CAD多边形主函数
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
  
  // 清空画布
  ctx.clearRect(0, 0, width, height);
  ctx.save();
  ctx.globalAlpha = state.opacity;

  // 设置变换：以CAD绘制区域中心为基准进行平移+缩放+旋转
  const centerX = dx + dw / 2 + state.offsetX;
  const centerY = dy + dh / 2 + state.offsetY;
  ctx.translate(centerX, centerY);
  ctx.rotate((state.rotation * Math.PI) / 180);
  ctx.scale(state.scale, state.scale);
  ctx.translate(-(dx + dw / 2), -(dy + dh / 2));


  state.polygons.forEach((poly, index) => {
    const isSelected = state.selectedIndices.has(index);
    const coords = poly.coordinates;
    if (!coords || coords.length < 3) return;

    // 将归一化坐标转换为画布像素坐标
    const canvasCoords = coords.map(([nx, ny]) => ({
      x: dx + nx * dw,
      y: dy + ny * dh
    }));


    ctx.fillStyle = 'rgba(255, 0, 0, 0.25)' 
    ctx.strokeStyle = '#ff0000';  
    ctx.lineWidth = 3;            
    
    // 绘制多边形路径
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



//CAD多边形拖拽相关
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
  
  // 超过拖拽阈值后正式进入拖拽模式
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
  
  // 如果没有发生拖拽，则视为点击事件
  if (!wasDragging && event) {
    handleCanvasClick(event);
  }
}

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

function handleCanvasClick(event) {
  if (state.isDragging) return; // 拖拽中不处理点击
  
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
  
  // 将点击坐标反向变换到CAD绘制区坐标系
  const rotationRad = -(state.rotation * Math.PI) / 180;
  const cos = Math.cos(rotationRad);
  const sin = Math.sin(rotationRad);
  let invX = (clickX - centerX) * cos - (clickY - centerY) * sin;
  let invY = (clickX - centerX) * sin + (clickY - centerY) * cos;
  invX = invX / state.scale + dx + dw / 2;
  invY = invY / state.scale + dy + dh / 2;
  
  // 逆序检测多边形（后绘制的在上层）
  let clickedIndex = -1;
  for (let i = state.polygons.length - 1; i >= 0; i--) {
    const poly = state.polygons[i];
    const coords = poly.coordinates;
    if (!coords || coords.length < 3) continue;
    
    // 转换为画布坐标进行碰撞检测
    const canvasCoords = coords.map(([px, py]) => ({
      x: dx + px * dw,
      y: dy + py * dh
    }));
    
    if (isPointInPolygon(invX, invY, canvasCoords)) {
      clickedIndex = i;
      break;
    }
  }
  
  if (clickedIndex === -1) return; // 未点击到任何多边形
  
  // 根据按键状态处理选择逻辑
  if (event.shiftKey) {
    // Shift+点击：添加到选中集合
    state.selectedIndices.add(clickedIndex);
  } else if (event.ctrlKey || event.metaKey) {
    // Ctrl/Cmd+点击：从选中集合移除
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



//CAD多边形缩放相关
function handleWheel(event) {
  event.preventDefault();
  const factor = event.deltaY > 0 ? 0.95 : 1.05;
  scale(factor);
}


function scale(factor) {
  // 使用较小的调整因子实现平滑缩放
  const adjustedFactor = factor > 1 ? 1.01 : 0.99;
  state.scale = Math.max(0.1, Math.min(10, state.scale * adjustedFactor));
  draw();
}

//CAD多边形旋转相关
function rotate(degrees) {
  state.rotation = (state.rotation + degrees) % 360;
  if (state.rotation < 0) state.rotation += 360;
  draw();
}

// 确认CAD多边形位置
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
  
  // 确定要导出的多边形：未选择则导出全部，否则导出选中的
  const polygonsToUse = state.selectedIndices.size === 0 
    ? state.polygons 
    : state.polygons.filter((_, index) => state.selectedIndices.has(index));

  // 转换每个多边形的坐标
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


  // 提交CAD多边形结果到父组件
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


// 监听事件
watch(
  () => state.rotation,
  () => draw()
);


watch(
  () => [props.autoMatchEnabled, state.isLoaded],
  ([enabled, loaded]) => {
    if (enabled && loaded && props.detectedContours && props.detectedContours.length > 0) {
      nextTick(() => {
        console.log('触发自动匹配，轮廓已确认，CAD已加载');
        autoMatchWithDetectedContoursOptimized();
      });
    }
  }
);

watch(
  () => props.detectedContours,
  (newContours) => {
    if (props.autoMatchEnabled && state.isLoaded && newContours && newContours.length > 0) {
      nextTick(() => {
        console.log('检测到轮廓变化，触发自动匹配');
        autoMatchWithDetectedContoursOptimized();
      });
    }
  },
  { deep: true }
);

//生命周期
onUnmounted(() => {
  document.removeEventListener('mousemove', onDrag);
  document.removeEventListener('mouseup', stopDrag);
  dragStartPos = null;
});


// ============ 核心优化：基于SVD的鲁棒形状匹配 ============

/**
 * Kabsch算法：使用SVD计算两个点集之间的最佳刚体变换（旋转+平移+缩放）
 * 比PCA方法更稳定，直接给出最优变换矩阵
 * @param {Array<[number, number]>} sourcePoints - 源点集（CAD轮廓）
 * @param {Array<[number, number]>} targetPoints - 目标点集（检测到的紫色轮廓）
 * @returns {Object} 变换参数 {rotation, translation, scale, rotationMatrix}
 */
function kabschAlgorithm(sourcePoints, targetPoints) {
  const n = sourcePoints.length;
  if (n !== targetPoints.length || n < 3) {
    throw new Error('点集数量不匹配或不足');
  }

  // 1. 计算质心
  const sourceCentroid = calculateCentroid(sourcePoints);
  const targetCentroid = calculateCentroid(targetPoints);

  // 2. 中心化点集（去均值）
  const sourceCentered = sourcePoints.map(p => [
    p[0] - sourceCentroid[0],
    p[1] - sourceCentroid[1]
  ]);
  const targetCentered = targetPoints.map(p => [
    p[0] - targetCentroid[0],
    p[1] - targetCentroid[1]
  ]);

  // 3. 构建协方差矩阵 H = P^T * Q （2x2矩阵）
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
  
  // 6. 处理反射情况（确保是正常旋转而非镜像）
  const det = R[0][0] * R[1][1] - R[0][1] * R[1][0];
  if (det < 0) {
    // 如果是反射，翻转V的最后一列以纠正为旋转
    Vt[1][0] = -Vt[1][0];
    Vt[1][1] = -Vt[1][1];
    R = matrixMultiply(transpose(Vt), transpose(U));
  }

  // 7. 从旋转矩阵提取旋转角度
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

  // 9. 计算缩放比例（基于点云分布尺度）
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
 * 2x2矩阵的SVD分解（简化Jacobi实现）
 * 适用于小矩阵的高性能计算，无需引入外部库
 * @param {Array<Array<number>>} A - 2x2输入矩阵
 * @returns {Object} {U, S, Vt} 分解结果
 */
function svd2x2(A) {
  const a = A[0][0], b = A[0][1], c = A[1][0], d = A[1][1];
  
  // 计算ATA的特征值
  const ata00 = a*a + c*c;
  const ata01 = a*b + c*d;
  const ata11 = b*b + d*d;
  
  // 特征值计算
  const trace = ata00 + ata11;
  const det = ata00 * ata11 - ata01 * ata01;
  const discriminant = Math.sqrt(trace*trace - 4*det);
  const s1 = Math.sqrt((trace + discriminant) / 2);
  const s2 = Math.sqrt((trace - discriminant) / 2);
  
  // 计算旋转角度
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
 * ICP（迭代最近点）算法：迭代优化变换参数以达到更精确对齐
 * 通过多次迭代：找最近点对应 -> 计算最优变换 -> 应用变换 -> 检查收敛
 * @param {Array<[number, number]>} sourcePoints - 源点集
 * @param {Array<[number, number]>} targetPoints - 目标点集
 * @param {number} maxIterations - 最大迭代次数
 * @param {number} tolerance - 收敛阈值
 * @returns {Object} 最优变换参数
 */
function iterativeClosestPoint(sourcePoints, targetPoints, maxIterations = 20, tolerance = 0.001) {
  let currentSource = [...sourcePoints];
  let bestTransform = null;
  let minError = Infinity;
  
  for (let iter = 0; iter < maxIterations; iter++) {
    // 1. 建立点对应关系：为每个源点找最近的目标点
    const correspondences = findClosestPoints(currentSource, targetPoints);
    
    // 2. 使用Kabsch计算当前迭代的最佳变换
    const transform = kabschAlgorithm(
      correspondences.map(c => c.source),
      correspondences.map(c => c.target)
    );
    
    // 3. 应用变换到源点集
    currentSource = sourcePoints.map(p => transformPoint(p, transform));
    
    // 4. 计算当前误差
    const error = calculateAlignmentError(currentSource, targetPoints, correspondences);
    
    // 5. 保存历史最佳结果
    if (error < minError) {
      minError = error;
      bestTransform = transform;
    }
    
    // 6. 收敛检查：误差足够小或变化足够小时停止
    if (error < tolerance || (iter > 0 && Math.abs(minError - error) < tolerance * 0.1)) {
      console.log(`ICP收敛于第${iter + 1}次迭代，误差: ${error.toFixed(4)}`);
      break;
    }
  }
  
  return bestTransform || kabschAlgorithm(sourcePoints, targetPoints);
}

/**
 * 为每个源点找到目标点集中的最近点（欧氏距离）
 * @param {Array<[number, number]>} sourcePoints 
 * @param {Array<[number, number]>} targetPoints 
 * @returns {Array<{source, target, distance}>} 对应关系数组
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
 * 计算对齐误差（均方根误差RMSE）
 * @param {Array<[number, number]>} sourcePoints 
 * @param {Array<[number, number]>} targetPoints 
 * @param {Array} correspondences - 点对应关系
 * @returns {number} RMSE误差值
 */
function calculateAlignmentError(sourcePoints, targetPoints, correspondences) {
  let totalError = 0;
  for (const c of correspondences) {
    totalError += c.distance * c.distance;
  }
  return Math.sqrt(totalError / correspondences.length);
}

// ============ 辅助函数 ============

/**
 * 计算点集质心
 * @param {Array<[number, number]>} points 
 * @returns {[number, number]} 质心坐标 [x, y]
 */
function calculateCentroid(points) {
  const sum = points.reduce((acc, p) => [acc[0] + p[0], acc[1] + p[1]], [0, 0]);
  return [sum[0] / points.length, sum[1] / points.length];
}

/**
 * 计算点云尺度（均方根距离）
 * 用于估计点集的整体大小，计算缩放比例
 * @param {Array<[number, number]>} points 
 * @returns {number} 尺度值
 */
function calculatePointCloudScale(points) {
  const centroid = calculateCentroid(points);
  let sumSq = 0;
  for (const p of points) {
    sumSq += Math.hypot(p[0] - centroid[0], p[1] - centroid[1]);
  }
  return sumSq / points.length;
}

/**
 * 使用变换参数变换单个点
 * 变换顺序：缩放 -> 旋转 -> 平移
 * @param {[number, number]} point 
 * @param {Object} transform 
 * @returns {[number, number]} 变换后的点
 */
function transformPoint(point, transform) {
  const { rotationMatrix, translation, scale } = transform;
  
  // 缩放
  const scaled = [point[0] * scale, point[1] * scale];
  
  // 旋转
  const rotated = [
    rotationMatrix[0][0] * scaled[0] + rotationMatrix[0][1] * scaled[1],
    rotationMatrix[1][0] * scaled[0] + rotationMatrix[1][1] * scaled[1]
  ];
  
  // 平移
  return [rotated[0] + translation[0], rotated[1] + translation[1]];
}

/**
 * 2x2矩阵乘法
 * @param {Array<Array<number>>} A 
 * @param {Array<Array<number>>} B 
 * @returns {Array<Array<number>>} 结果矩阵
 */
function matrixMultiply(A, B) {
  return [
    [A[0][0]*B[0][0] + A[0][1]*B[1][0], A[0][0]*B[0][1] + A[0][1]*B[1][1]],
    [A[1][0]*B[0][0] + A[1][1]*B[1][0], A[1][0]*B[0][1] + A[1][1]*B[1][1]]
  ];
}

/**
 * 矩阵转置
 * @param {Array<Array<number>>} M 
 * @returns {Array<Array<number>>} 转置后的矩阵
 */
function transpose(M) {
  return [[M[0][0], M[1][0]], [M[0][1], M[1][1]]];
}




// ============自动匹配算法部分===========

/**
 * 自动匹配主函数：将CAD轮廓与检测到的轮廓对齐
 * 流程：重采样 -> Kabsch初始对齐 -> ICP精化 -> 应用变换
 */
function autoMatchWithDetectedContoursOptimized() {
  if (!props.detectedContours || props.detectedContours.length === 0) {
    console.warn('没有检测到的轮廓进行匹配');
    return;
  }
  if (state.polygons.length === 0) {
    console.warn('没有CAD轮廓进行匹配');
    return;
  }
  const targetContour = props.detectedContours[0];
  if (!targetContour || !targetContour.coords || targetContour.coords.length < 3) {
    console.warn('未找到有效的目标轮廓进行匹配');
    return;
  }
  
  console.log('开始优化后的自动匹配，目标轮廓点数:', targetContour.coords.length);
  
  // 使用第一个CAD多边形作为源
  const cadPolygon = state.polygons[0];
  if (!cadPolygon || !cadPolygon.coordinates || cadPolygon.coordinates.length < 3) return;
  
  const dw = state.cadDrawWidth;
  const dh = state.cadDrawHeight;
  const dx = state.cadDrawOffsetX;
  const dy = state.cadDrawOffsetY;

  // 将CAD归一化坐标转换为画布像素坐标
  const cadPixelCoords = cadPolygon.coordinates.map(([nx, ny]) => [
    dx + nx * dw,
    dy + ny * dh
  ]);
  const targetPixelCoords = targetContour.coords.map(p => [p.x, p.y]);
  
  // ===== 核心匹配流程 =====
  
  // 降采样以提高计算效率
  const cadSampled = resamplePolygon(cadPixelCoords, 50);     
  const targetSampled = resamplePolygon(targetPixelCoords, 50);
  
  // 使用Kabsch算法获得初始变换估计
  let transform = kabschAlgorithm(cadSampled, targetSampled);
  
  // 使用ICP迭代精化
  if (cadSampled.length >= 10 && targetSampled.length >= 10) {
    try {
      const refinedTransform = iterativeClosestPoint(cadSampled, targetSampled, 15, 0.5);
      
      // 验证ICP结果是否显著优于初始结果（至少提升10%）
      const initialError = evaluateTransform(cadSampled, targetSampled, transform);
      const refinedError = evaluateTransform(cadSampled, targetSampled, refinedTransform);
      
      if (refinedError < initialError * 0.9) {
        transform = refinedTransform;
        console.log('采用ICP精化结果，误差降低:', ((initialError - refinedError) / initialError * 100).toFixed(1) + '%');
      }
    } catch (e) {
      console.warn('ICP精化失败，使用初始Kabsch结果:', e);
    }
  }
  
  // 将计算出的变换应用到Vue状态
  applyTransformToState(transform, dx, dy, dw, dh);
  
  draw();
  
  console.log('优化后的自动匹配完成:', {
    rotation: (transform.rotation * 180 / Math.PI).toFixed(1) + '°',
    scale: transform.scale.toFixed(3),
    offset: `(${state.offsetX.toFixed(1)}, ${state.offsetY.toFixed(1)})`
  });
}

// 多边形重采样
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

// 评估变换质量：计算变换后点集与目标点集的平均距离
function evaluateTransform(sourcePoints, targetPoints, transform) {
  const transformed = sourcePoints.map(p => transformPoint(p, transform));
  let totalError = 0;
  
  for (let i = 0; i < transformed.length; i++) {
    // 对每个变换后的点找最近的目标点
    let minDist = Infinity;
    for (const t of targetPoints) {
      const dist = Math.hypot(transformed[i][0] - t[0], transformed[i][1] - t[1]);
      minDist = Math.min(minDist, dist);
    }
    totalError += minDist;
  }
  
  return totalError / transformed.length;
}

//将数学变换参数应用到Vue响应式状态
function applyTransformToState(transform, dx, dy, dw, dh) {
  const { rotation, translation, scale } = transform;
  
  // 弧度转角度并归一化到0-360
  let rotationDeg = (rotation * 180 / Math.PI) % 360;
  if (rotationDeg < 0) rotationDeg += 360;
  state.rotation = rotationDeg;
  
  state.scale = scale;
  state.offsetX = translation[0];
  state.offsetY = translation[1];
}
</script>





<style scoped>
@import './CADstyle.css';
</style>

