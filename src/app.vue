<template>
  <div id="app" class="app-root">
    <header class="app-header">
      <div class="header-left">
        <div class="logo">🏙 CiityMind</div>
      </div>
      
      <!-- 工具栏按钮 - 修改后的部分 -->
      <div class="header-center">
        <div class="toolbar-dropdown" @mouseenter="showToolbar = true" @mouseleave="showToolbar = false">
          <button class="btn toolbar-btn dropdown-trigger">
            <span class="btn-text">工具栏（待完善）</span>
            <span class="dropdown-arrow">▼</span>
          </button>
          
          <div class="dropdown-menu" v-show="showToolbar">
            <button class="btn toolbar-btn" @click="summarizeReport">
              <span class="btn-icon">📄</span>
              <span class="btn-text">调研报告</span>
            </button>
            <button class="btn toolbar-btn" @click="analyzeStreetViews">
                <span class="btn-icon">🌆</span>
                <span class="btn-text">街景图分析</span>
            </button>

            <button class="btn toolbar-btn" @click="analyzeWithAI">
              <span class="btn-icon">🤖</span>
              <span class="btn-text">AI助手分析</span>
            </button>
            <button class="btn toolbar-btn" @click="generateSketch">
              <span class="btn-icon">✨</span>
              <span class="btn-text">三维渲染图</span>
            </button>

            <button class="btn toolbar-btn" @click="generateZoningPrompt">
              <span class="btn-icon">🗺️</span>
              <span class="btn-text">平面图</span>
            </button>

            <button class="btn toolbar-btn" @click="suggestEdits">
              <span class="btn-icon">✏️</span>
              <span class="btn-text">修改草图（待完善）</span>
            </button>
          </div>
        </div>
      </div>
      
      <div class="header-right">
          <button 
            class="btn toolbar-btn" 
            @click="showImageCollection"
            v-if="hasGeneratedImage"
            style="background: var(--accent-2);"
          >
            <span class="btn-text">查看图片集</span>
          </button>
      </div>
    </header>

    <div class="app-main" style="display:flex; gap:12px; padding:12px;">
      <!-- 左侧AI助手栏 -->
      <aside class="left-panel" style="width:360px; height: calc(100vh - 80px);">
        <div class="panel-title">
          AI助手
          <span class="status-indicator-right">
            <span class="status-dot"></span>
            <span class="status-text">在线</span>
          </span>
        </div>

        <!-- 聊天窗口部分 -->
        <div class="chat-window" style="height: calc(100vh - 200px); overflow-y:auto;">
          <div v-for="(m, idx) in messages" :key="idx" class="chat-msg" :class="{'from-user': m.role === 'user', 'from-system': m.role !== 'user'}">
            <div class="msg-content">{{ m.text }}</div>
          </div>
        </div>
        <div class="chat-input" style="margin-top:8px;">
          <textarea v-model="newMessage" @keydown.enter.exact.prevent="sendMessage" placeholder="输入消息并按 Enter 发送" style="width:100%;min-height:56px;"></textarea>
          <div style="margin-top:6px;">
            <button class="btn" @click="sendMessage">发送</button>
          </div>
        </div>
      </aside>

    <!-- 右侧地图区域 -->
    <section class="center-panel" style="flex:1; display:flex; flex-direction:column;">
      <div class="map-top" style="margin-bottom:8px;" v-show="currentPage === 'map' && !hasGeneratedImage">
        <div class="btn-group" style="margin-left: auto;">
          <button class="btn map-control-btn" v-if="!selectMode" @click="enterSelectMode">选择</button>
          <button class="btn map-control-btn" v-if="selectMode" @click="finishSelectMode">✅</button>
          <button class="btn map-control-btn" v-if="selectMode" @click="clearSelection">❌</button>
        </div>
      </div>

      <div class="content-wrapper" :style="{
        position: 'relative', 
        flex: 1, 
        minHeight: '400px',
      }">

        <!-- 地图页面 -->
        <div v-show="currentPage === 'map'" class="map-wrapper" style="width:100%; height:100%;">
          <div id="fudan-map" class="map-container" style="width:100%; height:100%;"></div>
          <canvas
            ref="overlayCanvas"
            :style="{ position: 'absolute', left:0, top:0, width:'100%', height:'100%', pointerEvents: selectMode ? 'auto' : 'none' }"
            @pointerdown="onPointerDown"
            @pointermove="onPointerMove"
            @pointerup="onPointerUp"
            @pointercancel="onPointerUp"
          ></canvas>
          
            <!-- 街景图上传确认对话框 -->
          <div v-if="showStreetViewUpload" class="street-view-dialog" 
              style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                      background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 1001;">
            <h3 style="margin: 0 0 15px 0;">上传街景图</h3>
            <p style="margin: 0 0 20px 0; color: #666;">是否在该位置上传街景图？</p>
            <div style="display: flex; gap: 10px; justify-content: flex-end;">
              <button class="btn" @click="cancelStreetViewUpload" 
                      style="background: #f0f0f0; color: #333;">取消</button>
              <button class="btn" @click="confirmStreetViewUpload" 
                      style="background: #1890ff; color: white; border: 1px solid #1890ff; padding: 8px 16px; border-radius: 4px;">
                确认
              </button>
            </div>
          </div>

          <!-- 技术经济指标信息窗口 -->
          <div v-if="showEconomicInfo" class="economic-info-window" 
               :style="{ left: infoWindowPosition.x + 'px', top: infoWindowPosition.y + 'px' }">
            <div class="info-header">
              <h3>保利悦活荟 - 技术经济指标</h3>
              <button class="close-btn" @click="closeEconomicInfo">×</button>
            </div>
            <div class="info-content" v-if="economicIndicators && Object.keys(filteredIndicators).length > 0">
              <div v-for="(value, key) in filteredIndicators" :key="key" class="indicator-row">
                <span class="label">{{ formatKey(key) }}:</span>
                <span class="value">{{ value }}</span>
              </div>
            </div>
            <div class="info-content" v-else-if="economicIndicators">
              <p>暂无技术经济指标数据</p>
            </div>
            <div class="info-content" v-else>
              <p>加载中...</p>
            </div>
          </div>
        </div>

        <!-- 图片集选择页面 -->
        <div v-show="currentPage === 'image-collection'" class="collection-wrapper" style="width:100%; height:100%; display:flex; flex-direction:column; justify-content:center; align-items:center; background:#f0f0f0; overflow:hidden; padding:20px;">
          <div style="text-align:center; margin-bottom:30px;">
            <h2 style="color:#333; margin-bottom:8px;">图片集</h2>
            <p style="color:#666;">选择要查看的图片集</p>
          </div>
          
          <div style="display:flex; gap:20px; justify-content:center; align-items:center; flex-wrap:wrap;">
            <!-- 三维渲染图集卡片 -->
            <div 
              class="collection-card" 
              @click="enterCollection('sketch')"
              :style="{
                opacity: imageCollections.sketch.images.length > 0 ? 1 : 0.6,
                cursor: imageCollections.sketch.images.length > 0 ? 'pointer' : 'not-allowed'
              }"
            >
              <div class="card-icon">✨</div>
              <h3>三维渲染图集</h3>
              <p>{{ imageCollections.sketch.images.length }} 张图片</p>
              <div v-if="imageCollections.sketch.images.length === 0" style="color:#999; font-size:12px;">
                暂无图片
              </div>
            </div>
            
            <!-- 功能分区图集卡片 -->
            <div 
              class="collection-card" 
              @click="enterCollection('zoning')"
              :style="{
                opacity: imageCollections.zoning.images.length > 0 ? 1 : 0.6,
                cursor: imageCollections.zoning.images.length > 0 ? 'pointer' : 'not-allowed'
              }"
            >
              <div class="card-icon">🗺️</div>
              <h3>功能分区图集</h3>
              <p>{{ imageCollections.zoning.images.length }} 张图片</p>
              <div v-if="imageCollections.zoning.images.length === 0" style="color:#999; font-size:12px;">
                暂无图片
              </div>
            </div>
          </div>
          
          <!-- 返回地图按钮 -->
          <button class="btn" @click="togglePage" style="margin-top:30px; padding:10px 20px;">
            返回地图
          </button>
        </div>

        <!-- 具体图片集浏览页面 -->
        <div v-show="currentPage === 'image'" class="image-wrapper" style="width:100%; height:100%; display:flex; flex-direction:column; justify-content:flex-start; align-items:center; background:#f0f0f0; overflow:hidden;">
          <div style="width:100%; padding:8px 16px; background:white; border-bottom:1px solid #e0e0e0; display:flex; justify-content:space-between; align-items:center; flex-shrink:0; min-height:50px;">
            <button class="btn" @click="backToCollection" style="display:flex; align-items:center; gap:6px;">
              ← 返回图片集
            </button>
            
            <!-- 标题和分页信息 -->
            <div style="display:flex; align-items:center; gap:12px;">
              <span style="font-weight:bold; font-size:16px;">
                {{ currentCollectionType === 'sketch' ? '三维渲染图集' : '功能分区图集' }}
              </span>
              <div v-if="getCurrentCollection().images.length > 1" style="display: flex; align-items: center; gap: 8px; font-size:14px; color:#666;">
                <span>图片 {{ getCurrentCollection().currentIndex + 1 }}/{{ getCurrentCollection().images.length }}</span>
              </div>
            </div>
          </div>

          <!-- 图片显示区域 -->
          <div style="flex:1; width:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:0; overflow:auto; position:relative;">
            
            <!-- 分页控制按钮 -->
            <div v-if="getCurrentCollection().images.length > 1" style="position:absolute; top:50%; left:0; right:0; display:flex; justify-content:space-between; align-items:center; padding:0 20px; z-index:10; pointer-events:none;">
              <button 
                class="btn" 
                @click="prevImage" 
                :disabled="getCurrentCollection().currentIndex === 0"
                style="pointer-events:auto; background:rgba(255,255,255,0.9); border-radius:50%; width:40px; height:40px; display:flex; align-items:center; justify-content:center; box-shadow:0 2px 8px rgba(0,0,0,0.2);"
              >←</button>
              
              <button 
                class="btn" 
                @click="nextImage" 
                :disabled="getCurrentCollection().currentIndex === getCurrentCollection().images.length - 1"
                style="pointer-events:auto; background:rgba(255,255,255,0.9); border-radius:50%; width:40px; height:40px; display:flex; align-items:center; justify-content:center; box-shadow:0 2px 8px rgba(0,0,0,0.2);"
              >→</button>
            </div>

            <!-- 图片容器 -->
            <div v-if="getCurrentImage()" style="max-width:95%; max-height:95%; display:flex; justify-content:center; align-items:center; padding:20px;">
              <img 
                :src="getCurrentImage()" 
                :alt="currentCollectionType === 'sketch' ? '三维渲染图' : '功能分区图'" 
                style="max-width:100%; max-height:100%; object-fit:contain; transition: all 0.3s ease; box-shadow: 0 4px 12px rgba(0,0,0,0.15); border-radius:4px;"
                @load="onImageLoad"
                @error="onImageError"
              >
            </div>
            
            <!-- 历史记录控制 -->
            <div v-if="getCurrentCollection().images.length > 0" style="display: flex; gap: 8px; align-items: center; margin-top:16px; padding:8px 16px; background:rgba(255,255,255,0.8); border-radius:8px;">
              <button
                class="btn"
                v-if="canRevertEdit()"
                @click="revertEdit"
                style="padding:6px 12px; font-size:12px;"
              >撤回修改</button>

              <button
                class="btn"
                v-if="canRestoreEdit()"
                @click="restoreEdit"
                style="padding:6px 12px; font-size:12px;"
              >回到修改</button>
            </div>
            
            <div v-else style="color:#666; text-align:center; padding:40px;">
              <p>暂无图片</p>
              <p style="font-size:12px; margin-top:8px;">请先生成图片</p>
            </div>
          </div>
        </div>
      </div>
    </section>
    </div>
  <!-- 街景图查看模态框部分 -->
  <div v-if="showStreetViewModal" class="street-view-modal" @click="closeStreetViewModal">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h3>街景图查看</h3>
        <button class="close-btn" @click="closeStreetViewModal">×</button>
      </div>
      <div class="modal-body">
        <img :src="currentStreetViewImage" alt="街景图" class="street-view-image" />
        <div class="image-info">
          <p>坐标: {{ currentStreetViewPosition.lng.toFixed(6) }}, {{ currentStreetViewPosition.lat.toFixed(6) }}</p>
          <p>上传时间: {{ formatStreetViewTime(currentStreetViewTime) }}</p>
        </div>
        
        <!-- 新增的问题描述输入区域 -->
        <div class="problem-description-section">
          <h4>问题描述</h4>
          <textarea 
            v-model="problemDescription" 
            placeholder="请输入关于此处街景图存在问题的描述..."
            class="problem-description-textarea"
            :disabled="isSavingProblem"
          ></textarea>
          
          <!-- 保存状态提示 -->
          <div v-if="saveProblemStatus" class="save-status" :class="saveProblemStatus.type">
            {{ saveProblemStatus.message }}
          </div>
          
          <div class="problem-description-buttons">
            <button 
              class="btn cancel-btn" 
              @click="cancelProblemDescription"
              :disabled="isSavingProblem"
            >取消</button>
            <button 
              class="btn confirm-btn" 
              @click="saveProblemDescription"
              :disabled="isSavingProblem || !problemDescription.trim()"
            >
              {{ isSavingProblem ? '保存中...' : '确定' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
  </div>


  <input 
    type="file" 
    ref="fileInput" 
    accept=".docx" 
    style="display: none" 
    @change="handleFileUpload"
  >
<input 
  type="file" 
  ref="streetViewFileInput" 
  accept="image/*" 
  style="display: none" 
  @change="handleStreetViewUpload"
>

</template>


<!--前端函数部分-->>
<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, computed} from 'vue';

//基础变量定义
// 地图基础配置相关
const messages = ref([{ role: 'system', text: '欢迎使用CityMind智能城市更新规划工具，我是助手小blue，很高兴为您服务😄。' }]);
const mapCenter = [121.475719, 31.342902]; // 中心：保利悦活荟
const mapInstance = ref(null);
const AMapRef = ref(null);
const showToolbar = ref(false);
const overlayCanvas = ref(null);
const selectMode = ref(false);
const economicIndicators = ref(null);
const showEconomicInfo = ref(false);
const infoWindowPosition = ref({ x: 0, y: 0 });
const selectState = reactive({
  drawing: false,
  points: [],          
  hasSelection: false,
  geoPoints: null,      
  currentPath: null    
});

// 调研报告相关
const fileInput = ref(null);
const isUploadingReport = ref(false);
const surveySummary = ref('');

// 街景图相关
const streetViewFileInput = ref(null);
const showStreetViewUpload = ref(false);
const streetViewPosition = ref(null);
const streetViewImages = ref([]);
const showStreetViewModal = ref(false);
const currentStreetViewImage = ref('');
const currentStreetViewPosition = ref({ lng: 0, lat: 0 });
const currentStreetViewTime = ref(0);
const problemDescription = ref('');
const streetViewProblemRecords = ref({});
const isSavingProblem = ref(false);
const saveProblemStatus = ref(null);
const isAnalyzingStreetViews = ref(false);
const streetViewAnalysisResults = ref([]);

// AI助手分析相关
const newMessage = ref('');
const isWaitingForStyleSuggestion = ref(false);
const isEditingSuggestion = ref(false);

// 三维渲染图相关
const imageCollections = ref({
  sketch: { 
    images: [],
    currentIndex: 0,
    history: [],
    currentHistoryIndex: []
  },
  zoning: { 
    images: [],
    currentIndex: 0,
    history: [],
    currentHistoryIndex: []
  }
});
const currentCollectionType = ref(null); 
const currentPage = ref('map');
const hasGeneratedImage = ref(false);

// 平面图相关
const isGeneratingZoningPrompt = ref(false);




//---------------------------------------------------------------------------------
//-----------------------------------基础功能模块-----------------------------------
//---------------------------------------------------------------------------------


// 加载高德JS api配置
function loadAMapScript(key = '3508dd8fea717dc69c9acf4b523d1a0f') {
  return new Promise((resolve, reject) => {
    if (window.AMap) return resolve(window.AMap);
    const src = `https://webapi.amap.com/maps?v=2.0&key=${key}`;
    const existing = document.querySelector(`script[src^="https://webapi.amap.com/maps"]`);
    if (existing) {
      existing.addEventListener('load', () => resolve(window.AMap));
      existing.addEventListener('error', reject);
      return;
    }
    const s = document.createElement('script');
    s.src = src; s.async = true;
    s.onload = () => window.AMap ? resolve(window.AMap) : reject(new Error('AMap loaded but undefined'));
    s.onerror = reject;
    document.head.appendChild(s);
  });
}


//加载高德地图基础部分
function initMap(AMap) {
  const map = new AMap.Map('fudan-map', {
    viewMode: '3D',
    center: mapCenter,
    zoom: 18,
    pitch: 40,
    rotation: -30,
    WebGLParams: { preserveDrawingBuffer: true },
    rotateEnable: true,
    pitchEnable: true,
    scrollWheel: true,
    doubleClickZoom: false
  });
  
  // 添加双击事件监听
  map.on('dblclick', function(e) {
    if (selectMode.value) return; // 选择模式下不触发
    handleMapDoubleClick(e);
  });

  AMap.plugin(['AMap.ToolBar', 'AMap.MapType'], function() {
    map.addControl(new AMap.ToolBar());
    const mapTypeCtrl = new AMap.MapType({
      defaultType: 1 // 0:二维地图，1:卫星图
    });
    map.addControl(mapTypeCtrl);
    
    // 初始隐藏控件
    setTimeout(() => {
      const layerItems = document.querySelectorAll('li.amap-ui-ctrl-layer-base-item');
      layerItems.forEach(item => {
        item.style.display = 'none';
      });
      
      const roadNetItems = document.querySelectorAll('li.amap-ui-ctrl-layer-overlay-item');
      roadNetItems.forEach(item => {
        const input = item.querySelector('input[data-id="AMap.TileLayer.RoadNet"]');
        if (input) {
          item.style.display = 'none';
        }
      });
      
      const trafficItems = document.querySelectorAll('li.amap-ui-ctrl-layer-overlay-item');
      trafficItems.forEach(item => {
        const input = item.querySelector('input[data-id="AMap.TileLayer.Traffic"]');
        if (input) {
          item.style.display = 'none';
        }
      });
    }, 1000); 
  });

  // 创建保利悦活荟标记添加点击事件
  const marker = new AMap.Marker({
    position: mapCenter,
    icon: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_b.png',
    offset: new AMap.Pixel(-12, -12),
    title: '保利悦活荟 - 技术经济指标'
  });
  marker.on('click', function(e) {
    handleMarkerClick(e);
  });
  map.add([marker]);
  mapInstance.value = map;
  AMapRef.value = AMap;
  
  // 选中基地区域与地图随动设定
  const redrawOn = ['moveend', 'zoomchange', 'dragging', 'dragend', 'rotatechange', 'pitchchange', 'resize', 'mapmove'];
  redrawOn.forEach(ev => {
    try { 
      map.on(ev, () => {
        setTimeout(redraw, 100); 
      }); 
    } catch(e) { 
      console.log('事件不支持:', ev, e);
    }
  });
  nextTick(() => { 
    resizeOverlayCanvas();
  });
}

function getCanvasCtx() {
  const c = overlayCanvas.value; if (!c) return null;
  return c.getContext('2d');
}

function resizeOverlayCanvas() {
  const c = overlayCanvas.value;
  const container = document.getElementById('fudan-map');
  if (!c || !container) return;
  const rect = container.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  c.style.width = rect.width + 'px';
  c.style.height = rect.height + 'px';
  c.width = Math.round(rect.width * dpr);
  c.height = Math.round(rect.height * dpr);
  const ctx = c.getContext('2d');
  if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  redraw();
}


//高德地图坐标转化相关工具函数
function lngLatToContainerPixel(llObj) {
  const map = mapInstance.value;
  const AMap = AMapRef.value;
  
  try {
    const lng = parseFloat(llObj.lng);
    const lat = parseFloat(llObj.lat);
    
    if (isNaN(lng) || isNaN(lat)) {
      console.error('坐标值无效:', { lng: llObj.lng, lat: llObj.lat });
      return null;
    }
    if (lng < -180 || lng > 180 || lat < -90 || lat > 90) {
      console.error('坐标范围无效:', { lng, lat });
      return null;
    }
    
    const lnglat = new AMap.LngLat(lng, lat);
    const p = map.lngLatToContainer(lnglat);
    
    if (!p) {
      console.error('坐标转换返回空值');
      return null;
    }
    
    return { 
      x: Math.round(p.getX()), 
      y: Math.round(p.getY()) 
    };
  } catch (e) {
    console.error('像素转换错误:', e);
    return null;
  }
}


//生命周期函数
onMounted(async () => {
  try {
    const AMap = await loadAMapScript();
    initMap(AMap);
  } catch (e) {
    console.error('地图加载失败', e);
    const el = document.getElementById('fudan-map');
    if (el) el.innerHTML = '<div style="padding:12px;color:#900">地图加载失败，请检查 key / network / 控制台错误。</div>';
  }
  nextTick(() => resizeOverlayCanvas());
  window.addEventListener('resize', resizeOverlayCanvas);
});

onBeforeUnmount(() => {
  if (mapInstance.value) {
    try { mapInstance.value.destroy && mapInstance.value.destroy(); } catch(e){}
    mapInstance.value = null;
  }
  window.removeEventListener('resize', resizeOverlayCanvas);
});

// 连接技术经济指标数据库
async function fetchEconomicIndicators() {
  try {
    const response = await fetch('http://127.0.0.1:5000/get-economic-indicators');
    const result = await response.json();
    
    if (result.ok) {
      economicIndicators.value = result.data;
      return true;
    } else {
      console.error('获取技术经济指标失败:', result.error);
      return false;
    }
  } catch (error) {
    console.error('获取技术经济指标时发生错误:', error);
    return false;
  }
}

// 过滤掉不需要显示的字段（如id, created_at等）
const filteredIndicators = computed(() => {
  if (!economicIndicators.value) return {};
  
  const excludeKeys = ['id', 'created_at'];
  const filtered = {};
  
  Object.keys(economicIndicators.value).forEach(key => {
    if (!excludeKeys.includes(key) && economicIndicators.value[key] !== null) {
      filtered[key] = economicIndicators.value[key];
    }
  });
  
  return filtered;
});

// 简单的字段名格式化函数（下划线转空格，首字母大写）
function formatKey(key) {
  return key.split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

// 处理地图标记点击事件
function handleMarkerClick(event) {
  const mapContainer = document.getElementById('fudan-map');
  if (mapContainer) {
    const rect = mapContainer.getBoundingClientRect();
    infoWindowPosition.value = {
      x: rect.width / 2 - 150,
      y: rect.height / 2 - 100  
    };
  }
  
  // 获取并显示技术经济指标
  fetchEconomicIndicators().then(success => {
    if (success) {
      showEconomicInfo.value = true;
    }
  });
}

function closeEconomicInfo() {
  showEconomicInfo.value = false;
}

//---------------------------------------------------------------------------------
//-----------------------------------街景图分析-----------------------------------
//---------------------------------------------------------------------------------
// 地图双击事件处理
function handleMapDoubleClick(event) {
  // 保存点击位置
  const newPosition = {
    lng: event.lnglat.getLng(),
    lat: event.lnglat.getLat()
  };
  
  // 显示上传确认对话框
  showStreetViewUpload.value = true;
  
  // 添加呼吸点标识，并保存标记引用
  const marker = addBreathingMarker(newPosition);
  
  if (!marker) {
    console.error('添加呼吸点标记失败');
    showStreetViewUpload.value = false;
    return;
  }
  
  // 保存当前上传的标记信息
  streetViewPosition.value = {
    position: newPosition,
    marker: marker
  };
}

// 添加呼吸点标识
function addBreathingMarker(position) {
  const AMap = AMapRef.value;
  if (!AMap || !mapInstance.value) {
    console.error('AMap或地图实例未初始化');
    return null;
  }
  
  try {
    // 创建HTML标记
    const markerDiv = document.createElement('div');
    markerDiv.className = 'html-breathing-marker';
    markerDiv.innerHTML = `
      <div class="breathing-dot"></div>
      <div class="breathing-ring ring-1"></div>
      <div class="breathing-ring ring-2"></div>
      <div class="breathing-ring ring-3"></div>
    `;
    
    // 添加样式确保标记可见，设置初始颜色为红色（完全红色）
    markerDiv.style.cssText = `
      width: 30px;
      height: 30px;
      position: relative;
      cursor: pointer;
    `;
    
    // 设置呼吸点初始为完全红色（移除白色背景）
    const dot = markerDiv.querySelector('.breathing-dot');
    if (dot) {
      dot.style.background = '#ff0000'; // 红色
      // 移除白色阴影效果
      dot.style.boxShadow = 'none';
    }
    
    const markerId = 'breathing_marker_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    
    const marker = new AMap.Marker({
      position: [position.lng, position.lat],
      content: markerDiv,
      offset: new AMap.Pixel(-15, -15),
      zIndex: 1000,
      title: '街景图上传点（临时）',
      extData: { 
        type: 'breathing_marker_temp',
        id: markerId, // 唯一标识
        isTemporary: true
      }
    });
    
    mapInstance.value.add([marker]);
    return marker;
        
  } catch (error) {
    console.error('添加HTML呼吸点标记失败:', error);
    return null;
  }
}

// 修改关闭街景图查看模态框函数
function closeStreetViewModal() {
  // 清空保存状态
  saveProblemStatus.value = null;
  isSavingProblem.value = false;
  
  showStreetViewModal.value = false;
  currentStreetViewImage.value = '';
  currentStreetViewPosition.value = { lng: 0, lat: 0 };
  currentStreetViewTime.value = 0;
  
  console.log('街景图查看模态框已关闭');
}

// 移除呼吸点标记
function removeBreathingMarker(marker) {
  if (!marker) return;
  
  try {
    // 从全局标记数组中移除
    if (window.streetViewMarkers) {
      const extData = marker.getExtData();
      if (extData && extData.id) {
        window.streetViewMarkers = window.streetViewMarkers.filter(m => {
          const mExtData = m.marker.getExtData();
          return !mExtData || mExtData.id !== extData.id;
        });
      }
    }
    
    // 移除地图上的标记
    mapInstance.value.remove([marker]);
    
    console.log('呼吸点标记已移除');
  } catch (error) {
    console.error('移除呼吸点标记失败:', error);
  }
}

// 确认上传街景图
function confirmStreetViewUpload() {
  showStreetViewUpload.value = false;
  // 触发文件选择器
  nextTick(() => {
    streetViewFileInput.value.click();
  });
}

// 取消上传
function cancelStreetViewUpload() {
  showStreetViewUpload.value = false;
  
  // 移除当前上传的呼吸点标记
  if (streetViewPosition.value && streetViewPosition.value.marker) {
    removeBreathingMarker(streetViewPosition.value.marker);
  }
  
  streetViewPosition.value = null;
  console.log('街景图上传已取消，呼吸点已移除');
}

// 处理街景图文件上传 - 修改成功处理部分
async function handleStreetViewUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  
  // 检查是否有有效的上传位置和标记
  if (!streetViewPosition.value || !streetViewPosition.value.marker) {
    alert('上传位置无效');
    return;
  }
  
  // 检查文件类型
  if (!file.type.startsWith('image/')) {
    alert('请选择图片文件');
    return;
  }
  
  try {
    const formData = new FormData();
    formData.append('street_view', file);
    formData.append('lng', streetViewPosition.value.position.lng);
    formData.append('lat', streetViewPosition.value.position.lat);
    
    const response = await fetch('http://127.0.0.1:5000/upload-street-view', {
      method: 'POST',
      body: formData
    });
    
    const result = await response.json();
    
    if (result.ok) {
      // 上传成功：将临时呼吸点标记转换为永久呼吸点标记（保持呼吸点样式）
      const success = convertToPermanentBreathingMarker(
        streetViewPosition.value.marker, 
        result.image_url, 
        streetViewPosition.value.position
      );
      
      if (success) {
        // 新增：自动打开街景图查看模态框
        showStreetViewImage(result.image_url, streetViewPosition.value.position, Date.now());
        
        messages.value.push({
          role: 'system',
          text: '街景图上传成功(长按呼吸点删除)！请输入街景图的问题描述。'
        });
        
        // 调试信息：检查标记是否真的存在
        setTimeout(() => {
          console.log('上传完成后检查标记状态:');
          console.log('- 当前地图标记数量:', window.streetViewMarkers ? window.streetViewMarkers.length : 0);
          console.log('- 标记数组:', window.streetViewMarkers);
        }, 1000);
        
      } else {
        messages.value.push({
          role: 'system',
          text: '街景图上传成功，但标记转换失败。'
        });
      }
      
    } else {
      // 上传失败：移除呼吸点
      messages.value.push({
        role: 'system',
        text: '街景图上传失败: ' + result.error
      });
      removeBreathingMarker(streetViewPosition.value.marker);
    }
  } catch (error) {
    // 网络错误：移除呼吸点
    messages.value.push({
      role: 'system',
      text: '上传街景图时发生错误: ' + error.message
    });
    removeBreathingMarker(streetViewPosition.value.marker);
  } finally {
    event.target.value = '';
    streetViewPosition.value = null;
    scrollToBottom();
  }
}

// 将临时呼吸点标记转换为永久呼吸点标记（保持呼吸点样式）
// 将临时呼吸点标记转换为永久呼吸点标记（保持呼吸点样式）
function convertToPermanentBreathingMarker(tempMarker, imageUrl, position) {
  const AMap = AMapRef.value;
  if (!AMap || !mapInstance.value || !tempMarker) return false;
  
  try {
    // 获取当前呼吸点标记的HTML内容
    const markerContent = tempMarker.getContent();
    if (!markerContent) {
      console.error('无法获取标记内容');
      return false;
    }
    
    // 更新标记的扩展数据，添加街景图信息
    tempMarker.setExtData({
      type: 'street_view_marker',
      imageUrl: imageUrl,
      position: position,
      timestamp: Date.now(),
      id: Date.now() + Math.random(), // 唯一标识
      isPermanent: true // 标记为永久标记
    });
    
    // 长按相关变量
    let longPressTimer = null;
    let isLongPress = false;
    
    // 添加鼠标按下事件 - 开始长按计时
    tempMarker.off('mousedown');
    tempMarker.on('mousedown', function(event) {
      event && event.stopPropagation && event.stopPropagation();
      isLongPress = false;
      longPressTimer = setTimeout(() => {
        isLongPress = true;
        showDeleteConfirmation(tempMarker, imageUrl, position);
      }, 800); // 800毫秒长按触发
    });
    
    // 添加鼠标抬起事件 - 取消长按
    tempMarker.off('mouseup');
    tempMarker.on('mouseup', function(event) {
      event && event.stopPropagation && event.stopPropagation();
      if (longPressTimer) {
        clearTimeout(longPressTimer);
        longPressTimer = null;
      }
      // 如果不是长按，则执行点击查看街景图
      if (!isLongPress) {
        showStreetViewImage(imageUrl, position, Date.now());
      }
      isLongPress = false;
    });
    
    // 添加鼠标移出事件 - 取消长按
    tempMarker.off('mouseout');
    tempMarker.on('mouseout', function(event) {
      if (longPressTimer) {
        clearTimeout(longPressTimer);
        longPressTimer = null;
      }
      isLongPress = false;
    });
    
    // 添加鼠标悬停效果 - 保持红色样式
    tempMarker.off('mouseover');
    tempMarker.off('mouseout');
    
    tempMarker.on('mouseover', function() {
      const markerElement = tempMarker.getContent();
      if (markerElement && markerElement.style) {
        markerElement.style.transform = 'scale(1.3)';
        markerElement.style.transition = 'transform 0.3s ease';
        // 呼吸点悬停时增加红色发光效果
        const dot = markerElement.querySelector('.breathing-dot');
        if (dot) {
          dot.style.background = '#ff0000'; // 红色
          dot.style.boxShadow = '0 0 10px #ff0000'; // 红色发光
        }
      }
    });
    
    tempMarker.on('mouseout', function() {
      const markerElement = tempMarker.getContent();
      if (markerElement && markerElement.style) {
        markerElement.style.transform = 'scale(1)';
        // 恢复呼吸点样式为红色
        const dot = markerElement.querySelector('.breathing-dot');
        if (dot) {
          dot.style.background = '#ff0000'; // 红色
          dot.style.boxShadow = 'none';
        }
      }
    });
    
    // 更新标记标题
    tempMarker.setTitle('街景图查看点（点击查看，长按删除）');
    
    // 保存到全局标记数组（确保数组存在）
    if (!window.streetViewMarkers) {
      window.streetViewMarkers = [];
    }
    window.streetViewMarkers.push({
      marker: tempMarker,
      imageUrl: imageUrl,
      position: position,
      timestamp: Date.now(),
      isBreathingStyle: true // 标记为呼吸点样式
    });
    
    console.log('临时呼吸点标记已转换为永久标记，当前标记数量:', window.streetViewMarkers.length);
    console.log('标记详细信息:', {
      imageUrl: imageUrl,
      position: position,
      marker: tempMarker,
      style: 'breathing_red' // 红色呼吸点样式
    });
    
    return true;
    
  } catch (error) {
    console.error('转换呼吸点标记失败:', error);
    return false;
  }
}

// 显示删除确认对话框
function showDeleteConfirmation(marker, imageUrl, position) {
  // 创建确认对话框
  const dialogDiv = document.createElement('div');
  dialogDiv.className = 'delete-confirmation-dialog';
  dialogDiv.innerHTML = `
    <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); 
                z-index: 1002; min-width: 250px; text-align: center;">
      <h3 style="margin: 0 0 15px 0; color: #333;">删除街景标记</h3>
      <p style="margin: 0 0 20px 0; color: #666;">确定要删除这个街景标记吗？</p>
      <div style="display: flex; gap: 10px; justify-content: center;">
        <button class="btn cancel-delete-btn" 
                style="background: #f0f0f0; color: #333; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer;">
          取消
        </button>
        <button class="btn confirm-delete-btn" 
                style="background: #ff4d4f; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer;">
          确认删除
        </button>
      </div>
    </div>
  `;
  
  // 添加到地图容器
  const mapContainer = document.getElementById('fudan-map');
  if (mapContainer) {
    mapContainer.appendChild(dialogDiv);
    
    // 添加事件监听
    const cancelBtn = dialogDiv.querySelector('.cancel-delete-btn');
    const confirmBtn = dialogDiv.querySelector('.confirm-delete-btn');
    
    const removeDialog = () => {
      if (mapContainer.contains(dialogDiv)) {
        mapContainer.removeChild(dialogDiv);
      }
    };
    
    cancelBtn.onclick = removeDialog;
    
    confirmBtn.onclick = () => {
      removeDialog();
      deleteStreetViewMarker(marker, imageUrl);
    };
    
    // 点击对话框外部也取消
    dialogDiv.onclick = (e) => {
      if (e.target === dialogDiv) {
        removeDialog();
      }
    };
  }
}

// 删除街景标记和相关照片
function deleteStreetViewMarker(marker, imageUrl) {
  if (!marker) return;
  
  try {
    // 从全局标记数组中移除
    if (window.streetViewMarkers) {
      const extData = marker.getExtData();
      if (extData && extData.id) {
        window.streetViewMarkers = window.streetViewMarkers.filter(m => {
          const mExtData = m.marker.getExtData();
          return !mExtData || mExtData.id !== extData.id;
        });
      }
    }
    
    // 移除地图上的标记
    mapInstance.value.remove([marker]);
    
    console.log('街景标记删除成功');
    messages.value.push({
      role: 'system',
      text: '街景标记已成功删除'
    });
    
    scrollToBottom();
    
  } catch (error) {
    console.error('删除街景标记失败:', error);
    messages.value.push({
      role: 'system',
      text: '删除标记时发生错误: ' + error.message
    });
    scrollToBottom();
  }
}

// 为呼吸点标记添加街景图查看功能
function addStreetViewClickEvent(position, imageUrl) {
  if (!window.currentBreathingMarker) return;
  
  // 保存街景图信息到呼吸点标记的扩展数据
  window.currentBreathingMarker.setExtData({
    type: 'street_view_marker',
    imageUrl: imageUrl,
    position: position,
    timestamp: Date.now()
  });
  
  // 添加点击事件监听
  window.currentBreathingMarker.on('click', function(event) {
    // 阻止事件冒泡，避免触发地图的其他点击事件
    event && event.stopPropagation && event.stopPropagation();
    
    const extData = window.currentBreathingMarker.getExtData();
    if (extData && extData.imageUrl) {
      showStreetViewImage(extData.imageUrl, extData.position, extData.timestamp);
    }
  });
  
  // 添加鼠标悬停效果
  window.currentBreathingMarker.on('mouseover', function() {
    const markerElement = window.currentBreathingMarker.getContent();
    if (markerElement && markerElement.style) {
      markerElement.style.transform = 'scale(1.2)';
      markerElement.style.transition = 'transform 0.3s ease';
    }
  });
  
  window.currentBreathingMarker.on('mouseout', function() {
    const markerElement = window.currentBreathingMarker.getContent();
    if (markerElement && markerElement.style) {
      markerElement.style.transform = 'scale(1)';
    }
  });
  
  console.log('街景图点击事件已添加到呼吸点标记');
}

// 添加街景图标记到地图
function addStreetViewMarker(position, imageUrl) {
  const AMap = AMapRef.value;
  if (!AMap || !mapInstance.value) return;
  
  // 创建街景图标记的HTML内容
  const markerDiv = document.createElement('div');
  markerDiv.className = 'street-view-marker';
  markerDiv.innerHTML = `
    <div class="camera-icon">📷</div>
  `;
  
  const marker = new AMap.Marker({
    position: [position.lng, position.lat],
    content: markerDiv,
    offset: new AMap.Pixel(-12, -12),
    zIndex: 999,
    title: '街景图查看点'
  });
  
  // 添加点击事件查看街景图
  marker.on('click', function() {
    showStreetViewImage(imageUrl, position);
  });
  
  mapInstance.value.add([marker]);
  
  // 保存标记信息
  if (!window.streetViewMarkers) {
    window.streetViewMarkers = [];
  }
  window.streetViewMarkers.push({
    marker: marker,
    imageUrl: imageUrl,
    position: position
  });
}

// 显示街景图
function showStreetViewImage(imageUrl, position, timestamp = null) {
  // 确保URL格式正确
  let fullImageUrl = imageUrl;
  if (!imageUrl.startsWith('http') && !imageUrl.startsWith('data:')) {
    fullImageUrl = `http://127.0.0.1:5000${imageUrl}`;
  }
  
  currentStreetViewImage.value = fullImageUrl;
  currentStreetViewPosition.value = position;
  currentStreetViewTime.value = timestamp || Date.now();
  
  // 清空之前的问题描述
  problemDescription.value = '';
  
  // 检查是否有保存的问题记录
  if (streetViewProblemRecords.value[fullImageUrl]) {
    problemDescription.value = streetViewProblemRecords.value[fullImageUrl];
  }
  
  showStreetViewModal.value = true;
  
  console.log('显示街景图:', {
    url: fullImageUrl,
    position: position,
    timestamp: currentStreetViewTime.value,
    modalVisible: showStreetViewModal.value
  });
}

// 修改保存问题描述函数
// 修改后的 saveProblemDescription 函数
async function saveProblemDescription() {
  if (!currentStreetViewImage.value || !problemDescription.value.trim()) return;
  
  isSavingProblem.value = true;
  saveProblemStatus.value = null;
  
  try {
    const imageUrl = currentStreetViewImage.value;
    const position = currentStreetViewPosition.value;
    const description = problemDescription.value.trim();
    
    // 调用后端API保存问题描述
    const response = await fetch('http://127.0.0.1:5000/save-problem-description', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        image_url: imageUrl,
        position: position,
        problem_description: description,
        timestamp: Date.now()
      })
    });
    
    const result = await response.json();
    
    if (result.ok) {
      // 保存问题描述到本地记录
      streetViewProblemRecords.value[imageUrl] = description;
      
      saveProblemStatus.value = {
        type: 'success',
        message: ''
      };
      
      // 关闭模态框
      setTimeout(() => {
        closeStreetViewModal();
      }, 1000);
      
    } else {
      throw new Error(result.error || '保存失败');
    }
    
  } catch (error) {
    saveProblemStatus.value = {
      type: 'error',
      message: '保存失败，请重试：' + error.message
    };
  } finally {
    isSavingProblem.value = false;
    scrollToBottom();
  }
}


// 修改取消问题描述函数
function cancelProblemDescription() {
  // 恢复原来的问题描述（如果有）
  if (currentStreetViewImage.value && streetViewProblemRecords.value[currentStreetViewImage.value]) {
    problemDescription.value = streetViewProblemRecords.value[currentStreetViewImage.value];
  } else {
    problemDescription.value = '';
  }
  
  // 清空保存状态
  saveProblemStatus.value = null;

}

// 在 script 部分的任意位置添加这个函数
function formatStreetViewTime(timestamp) {
  if (!timestamp) return '未知时间';
  
  const date = new Date(timestamp);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');
  
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}


async function captureMapSnapshot(hideOtherMarkers = false, keepMarker = null) {
    return new Promise((resolve) => {
        const map = mapInstance.value;
        if (!map) {
            resolve(null);
            return;
        }
        
        // 保存原始标记可见状态
        let originalVisibility = [];
        if (hideOtherMarkers && window.streetViewMarkers && window.streetViewMarkers.length > 0) {
            originalVisibility = window.streetViewMarkers.map(markerInfo => {
                let visible = true;
                try {
                    if (markerInfo.marker && typeof markerInfo.marker.getVisible === 'function') {
                        visible = markerInfo.marker.getVisible();
                    }
                } catch (e) {
                    console.warn('获取标记可见状态失败:', e);
                }
                return { marker: markerInfo.marker, visible: visible };
            });
            
            // 隐藏其他标记
            window.streetViewMarkers.forEach(markerInfo => {
                try {
                    if (markerInfo.marker && markerInfo.marker !== keepMarker) {
                        const markerContent = markerInfo.marker.getContent();
                        if (markerContent && markerContent.style) {
                            markerContent.style.display = 'none';
                        }
                        if (markerInfo.marker && typeof markerInfo.marker.setVisible === 'function' && markerInfo.marker !== keepMarker) {
                            markerInfo.marker.setVisible(false);
                        }
                    }
                } catch (e) {
                    console.warn('隐藏标记失败:', e);
                }
            });
        }
        
        // 确保当前标记可见
        if (keepMarker) {
            try {
                const markerContent = keepMarker.getContent();
                if (markerContent && markerContent.style) {
                    markerContent.style.display = '';
                    markerContent.style.zIndex = '10000'; // 确保在最上层
                }
                if (typeof keepMarker.setVisible === 'function') {
                    keepMarker.setVisible(true);
                }
            } catch (e) {
                console.warn('显示当前标记失败:', e);
            }
        }
        
        const container = map.getContainer ? map.getContainer() : document.getElementById('fudan-map');
        
        // 使用新的截图方法：同时捕获canvas和HTML标记
        captureMapWithMarkers(container, keepMarker).then(dataURL => {
            // 安全地恢复标记可见状态
            if (hideOtherMarkers) {
                safeRestoreMarkerVisibility(originalVisibility);
            }
            resolve(dataURL);
        }).catch(error => {
            console.error('截图失败:', error);
            // 安全地恢复标记可见状态
            if (hideOtherMarkers) {
                safeRestoreMarkerVisibility(originalVisibility);
            }
            resolve(null);
        });
    });
}

async function captureMapWithMarkers(container, keepMarker = null) {
    return new Promise(async (resolve, reject) => {
        try {
            // 首先获取地图canvas截图
            const mapCanvas = findMapCanvas(container);
            if (!mapCanvas) {
                reject(new Error('未找到地图canvas'));
                return;
            }
            
            // 创建临时canvas用于合成
            const tempCanvas = document.createElement('canvas');
            const tempCtx = tempCanvas.getContext('2d');
            const dpr = window.devicePixelRatio || 1;
            
            tempCanvas.width = mapCanvas.width;
            tempCanvas.height = mapCanvas.height;
            
            // 绘制地图背景
            tempCtx.drawImage(mapCanvas, 0, 0);
            
            // 如果有需要显示的标记，绘制标记
            if (keepMarker) {
                await drawMarkerToCanvas(keepMarker, tempCtx, container, mapCanvas);
            }
            
            // 转换为DataURL
            const dataURL = tempCanvas.toDataURL('image/png');
            resolve(dataURL);
            
        } catch (error) {
            reject(error);
        }
    });
}

async function drawMarkerToCanvas(marker, ctx, container, mapCanvas) {
    return new Promise((resolve) => {
        try {
            const markerContent = marker.getContent();
            if (!markerContent) {
                resolve();
                return;
            }
            
            // 获取标记在地图容器中的位置
            const position = marker.getPosition();
            if (!position) {
                resolve();
                return;
            }
            
            // 将经纬度转换为容器像素坐标
            const pixelPos = mapInstance.value.lngLatToContainer(position);
            if (!pixelPos) {
                resolve();
                return;
            }
            
            const markerRect = markerContent.getBoundingClientRect();
            const containerRect = container.getBoundingClientRect();
            
            // 计算标记在canvas中的位置
            const scaleX = mapCanvas.width / containerRect.width;
            const scaleY = mapCanvas.height / containerRect.height;
            
            const canvasX = (pixelPos.getX() - markerRect.width / 2) * scaleX;
            const canvasY = (pixelPos.getY() - markerRect.height / 2) * scaleY;
            const markerWidth = markerRect.width * scaleX;
            const markerHeight = markerRect.height * scaleY;
            
            // 创建临时canvas绘制标记
            const markerCanvas = document.createElement('canvas');
            markerCanvas.width = markerRect.width;
            markerCanvas.height = markerRect.height;
            const markerCtx = markerCanvas.getContext('2d');
            
            // 设置标记样式
            markerCtx.fillStyle = '#ff0000';
            markerCtx.strokeStyle = '#ffffff';
            markerCtx.lineWidth = 2;
            
            // 绘制呼吸点效果
            const centerX = markerRect.width / 2;
            const centerY = markerRect.height / 2;
            const maxRadius = Math.min(markerRect.width, markerRect.height) / 2;
            
            // 绘制呼吸动画效果（三个同心圆）
            for (let i = 0; i < 3; i++) {
                const radius = maxRadius * (0.7 - i * 0.15);
                const alpha = 0.7 - i * 0.2;
                
                markerCtx.beginPath();
                markerCtx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
                markerCtx.fillStyle = `rgba(255, 0, 0, ${alpha})`;
                markerCtx.fill();
                markerCtx.strokeStyle = `rgba(255, 255, 255, ${alpha})`;
                markerCtx.stroke();
            }
            
            // 绘制中心点
            markerCtx.beginPath();
            markerCtx.arc(centerX, centerY, maxRadius * 0.2, 0, 2 * Math.PI);
            markerCtx.fillStyle = 'rgba(255, 0, 0, 0.9)';
            markerCtx.fill();
            
            // 将标记绘制到主canvas上
            ctx.drawImage(markerCanvas, canvasX, canvasY, markerWidth, markerHeight);
            
            resolve();
            
        } catch (error) {
            console.error('绘制标记到canvas失败:', error);
            resolve();
        }
    });
}

function safeRestoreMarkerVisibility(visibilityArray) {
    if (!visibilityArray || !Array.isArray(visibilityArray)) return;
    
    visibilityArray.forEach(item => {
        try {
            if (item.marker) {
                // 恢复HTML显示
                const markerContent = item.marker.getContent();
                if (markerContent && markerContent.style) {
                    markerContent.style.display = '';
                    markerContent.style.zIndex = ''; // 恢复默认z-index
                }
                
                // 恢复地图标记可见性
                if (typeof item.marker.setVisible === 'function') {
                    item.marker.setVisible(item.visible);
                }
            }
        } catch (e) {
            console.warn('恢复标记可见性失败:', e);
        }
    });
}

// 修改后的 analyzeStreetViews 函数
async function analyzeStreetViews() {
  if (!window.streetViewMarkers || window.streetViewMarkers.length === 0) {
    messages.value.push({
      role: 'system',
      text: '暂无街景图标记，请先上传街景图。'
    });
    scrollToBottom();
    return;
  }
  
  isAnalyzingStreetViews.value = true;
  messages.value.push({
    role: 'system',
    text: `开始分析 ${window.streetViewMarkers.length} 个街景图点...`
  });
  scrollToBottom();
  
  try {
    const analyses = [];
    
    // 逐个处理每个街景图标记
    for (let i = 0; i < window.streetViewMarkers.length; i++) {
      const markerInfo = window.streetViewMarkers[i];
      
      // 确保当前标记可见
      try {
        const markerContent = markerInfo.marker.getContent();
        if (markerContent && markerContent.style) {
          markerContent.style.display = '';
        }
        if (typeof markerInfo.marker.setVisible === 'function') {
          markerInfo.marker.setVisible(true);
        }
      } catch (e) {
        console.warn('确保标记可见失败:', e);
      }
      
      // 截取地图截图
      const mapSnapshot = await captureMapSnapshot(true, markerInfo.marker);
      
      // 获取街景图数据和问题描述
      const streetImageUrl = markerInfo.imageUrl;
      const position = markerInfo.position;
      
      // 关键修改：正确获取问题描述
      // 尝试多种可能的键来获取问题描述
      const fullImageUrl = streetImageUrl.startsWith('http') ? streetImageUrl : `http://127.0.0.1:5000${streetImageUrl}`;
      const description = streetViewProblemRecords.value[streetImageUrl] || 
                         streetViewProblemRecords.value[fullImageUrl] || 
                         streetViewProblemRecords.value[markerInfo.imageUrl] || 
                         '用户未提供具体问题描述';
      
      // 调试信息
      console.log('问题描述获取详情:', {
        原始URL: streetImageUrl,
        完整URL: fullImageUrl,
        标记URL: markerInfo.imageUrl,
        问题描述: description,
        所有记录: Object.keys(streetViewProblemRecords.value)
      });
      
      // 构建分析数据（包含问题描述）
      analyses.push({
        map_image_data: mapSnapshot,
        street_image_data: streetImageUrl,
        description: description, // 新增：传递问题描述
        position: position
      });
      
      scrollToBottom();
    }
    
    if (analyses.length === 0) {
      messages.value.push({
        role: 'system',
        text: '无有效数据可分析'
      });
      return;
    }
    
    // 发送批量分析请求（包含问题描述）
    messages.value.push({
      role: 'system',
      text: `正在调用AI分析 ${analyses.length} 个街景图点...`
    });
    scrollToBottom();
    
    const response = await fetch('http://127.0.0.1:5000/analyze-street-views', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        analyses: analyses
      })
    });
    
    const result = await response.json();
    
    if (result.ok && result.results) {
      // 保存分析结果
      streetViewAnalysisResults.value = result.results;
      
      // 在聊天窗口显示分析结果
      result.results.forEach((item, index) => {
        if (item.analysis && !item.error) {
          messages.value.push({
            role: 'system',
            text: `📍 街景点分析报告（位置：${item.position.lng?.toFixed(6) || '未知'}, ${item.position.lat?.toFixed(6) || '未知'}）:\n${item.analysis}`
          });
        } else if (item.error) {
          messages.value.push({
            role: 'system',
            text: `❌ 第${item.index + 1}个点分析失败: ${item.error}`
          });
        }
      });
      
      messages.value.push({
        role: 'system',
        text: `✅ 街景图分析完成！共成功分析 ${result.results.filter(r => r.analysis).length} 个点，失败 ${result.results.filter(r => r.error).length} 个点。`
      });
      
    } else {
      messages.value.push({
        role: 'system',
        text: '街景图分析请求失败: ' + (result.error || '未知错误')
      });
    }
    
  } catch (error) {
    console.error('街景图分析错误:', error);
    messages.value.push({
      role: 'system',
      text: '街景图分析时发生错误: ' + error.message
    });
  } finally {
    isAnalyzingStreetViews.value = false;
    scrollToBottom();
  }
}

//---------------------------------------------------------------------------------
//-----------------------------------基地选区设计-----------------------------------
//---------------------------------------------------------------------------------

// 多边形绘制工具函数
function onPointerDown(e) {
  if (!selectMode.value) return;
  const c = overlayCanvas.value;
  if (!c) return;
  c.setPointerCapture && c.setPointerCapture(e.pointerId);
  selectState.drawing = true;
  const rect = c.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  selectState.points = [{x, y}];
  selectState.currentPath = [{x, y}];
  selectState.hasSelection = false;
  selectState.geoPoints = null;
  redraw();
}

function onPointerMove(e) {
  if (!selectMode.value || !selectState.drawing) return;
  const c = overlayCanvas.value;
  if (!c) return;
  const rect = c.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  selectState.currentPath.push({x, y});
  redraw();
}

function onPointerUp(e) {
  if (!selectMode.value) return;
  const c = overlayCanvas.value;
  if (!c) return;
  try { c.releasePointerCapture && c.releasePointerCapture(e.pointerId); } catch {}
  
  if (!selectState.drawing) return;
  selectState.drawing = false;
  
  // 完成绘制，保存最终路径
  if (selectState.currentPath && selectState.currentPath.length > 2) {
    selectState.points = [...selectState.currentPath];
    selectState.hasSelection = true;
    saveGeoPointsFromScreen(selectState.points);
  } else {
    selectState.hasSelection = false;
    selectState.points = [];
    selectState.geoPoints = null;
  }
  redraw();
}

//绘画主函数
function redraw() {
  const ctx = getCanvasCtx();
  const c = overlayCanvas.value;
  if (!ctx || !c) return;
  
  const cssW = c.clientWidth, cssH = c.clientHeight;
  ctx.clearRect(0, 0, cssW, cssH);
  
  // 绘制已完成的选区
  if (selectState.hasSelection && selectState.geoPoints && selectState.geoPoints.length > 0) {
    const screenPoints = [];
    for (const geoPoint of selectState.geoPoints) {
      const screenPoint = lngLatToContainerPixel(geoPoint);
      if (screenPoint) {
        // 添加补偿，确保前后一致
        screenPoints.push(adjustPixelForRedraw(screenPoint));
      }
    }
    
    if (screenPoints.length > 1) {
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(screenPoints[0].x, screenPoints[0].y);
      for (let i = 1; i < screenPoints.length; i++) {
        ctx.lineTo(screenPoints[i].x, screenPoints[i].y);
      }
      ctx.closePath();
      
      // 填充区域与边框
      ctx.fillStyle = 'rgba(0, 191, 255, 0.15)';
      ctx.fill();
      ctx.strokeStyle = '#00bfff';
      ctx.lineWidth = 3;
      ctx.stroke();
      ctx.restore();
    }
  }
  
  // 绘制中的路径
  if (selectState.drawing && selectState.currentPath && selectState.currentPath.length > 1) {
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(selectState.currentPath[0].x, selectState.currentPath[0].y);
    for (let i = 1; i < selectState.currentPath.length; i++) {
      ctx.lineTo(selectState.currentPath[i].x, selectState.currentPath[i].y);
    }
    
    // 绘制中的路径为红色，虚线
    ctx.strokeStyle = '#ff0000';
    ctx.lineWidth = 3;
    ctx.setLineDash([5, 5]); 
    ctx.stroke();
    ctx.restore();
  }
}

// 重绘时的像素调整函数
function adjustPixelForRedraw(pixel) {
  const map = mapInstance.value;
  try {
    const pitch = map.getPitch ? map.getPitch() : 0;
    const rotation = map.getRotation ? map.getRotation() : 0;
    const centerX = overlayCanvas.value ? overlayCanvas.value.clientWidth / 2 : 0;
    const centerY = overlayCanvas.value ? overlayCanvas.value.clientHeight / 2 : 0;
    
    const dx = pixel.x - centerX;
    const dy = pixel.y - centerY;
    
    // 根据地图倾斜角度进行补偿
    const pitchFactor = pitch / 90; 
    const adjustedDy = dy * (1 + pitchFactor * 0.15);
    
    // 根据旋转角度进行补偿
    const rotationRad = rotation * Math.PI / 180;
    const adjustedDx = dx * (1 + Math.abs(Math.sin(rotationRad)) * 0.1);
    
    return {
      x: centerX + adjustedDx,
      y: centerY + adjustedDy
    };
  } catch (error) {
    console.error('重绘像素调整错误:', error);
    return pixel;
  }
}


//多边形坐标保存
function saveGeoPointsFromScreen(points) {
  const geoPoints = [];
  for (const point of points) {
    const lngLat = containerPixelToLngLat(point);
    if (lngLat) {
      geoPoints.push({
        lng: parseFloat(lngLat.lng.toFixed(6)),
        lat: parseFloat(lngLat.lat.toFixed(6))
      });
    }
  }
  selectState.geoPoints = geoPoints.length > 0 ? geoPoints : null;
}

function containerPixelToLngLat(pixel) {
  const map = mapInstance.value;
  const AMap = AMapRef.value;
  if (!map || !AMap || !pixel) return null;
  
  try {
    // 获取当前地图状态
    const pitch = map.getPitch ? map.getPitch() : 0;
    const rotation = map.getRotation ? map.getRotation() : 0;
    
    // 考虑地图倾斜和旋转的补偿
    const adjustedPixel = adjustPixelForMapState(pixel, pitch, rotation);
    const p = new AMap.Pixel(adjustedPixel.x, adjustedPixel.y);
    const lnglat = map.containerToLngLat(p);
    if (!lnglat) return null;
    
    return { 
      lng: parseFloat(lnglat.getLng().toFixed(6)), 
      lat: parseFloat(lnglat.getLat().toFixed(6)) 
    };
  } catch (e) {
    console.error('坐标转换错误:', e);
    return null;
  }
}

function adjustPixelForMapState(pixel, pitch, rotation) {
  const centerX = overlayCanvas.value ? overlayCanvas.value.width / 2 : 0;
  const centerY = overlayCanvas.value ? overlayCanvas.value.height / 2 : 0;
  const dx = pixel.x - centerX;
  const dy = pixel.y - centerY;
  const pitchFactor = pitch / 60; 
  const adjustedDy = dy * (1 - pitchFactor * 0.1);
  return {
    x: centerX + dx,
    y: centerY + adjustedDy
  };
}




//---------------------------------------------------------------------------------
//-----------------------------------地图截图设计-----------------------------------
//---------------------------------------------------------------------------------


// 裁剪图片工具函数
function cropImage(canvas, container, rect) {
  return new Promise((resolve) => {
    const img = new Image();
    img.src = canvas.toDataURL('image/png');

    img.onload = () => {
      const cssW = container.clientWidth;
      const cssH = container.clientHeight;
      const imgW = img.width;
      const imgH = img.height;
      const scaleX = imgW / cssW;
      const scaleY = imgH / cssH;
      const sx = Math.round(rect.x * scaleX);
      const sy = Math.round(rect.y * scaleY);
      const sw = Math.round(rect.w * scaleX);
      const sh = Math.round(rect.h * scaleY);
      if (sw <= 0 || sh <= 0) {
        resolve(null);
        return;
      }

      const cutCanvas = document.createElement('canvas');
      cutCanvas.width = sw;
      cutCanvas.height = sh;
      const ctx = cutCanvas.getContext('2d');
      ctx.drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh);
      const selectionBase64 = cutCanvas.toDataURL('image/png');
      resolve(selectionBase64);
    };
    img.onerror = () => resolve(null);
  });
}

function findMapCanvas(container) {
  if (!container) return null;
  const canvases = Array.from(container.querySelectorAll('canvas'));
  if (canvases.length === 0) return null;
  for (const c of canvases) {
    try {
      const gl = c.getContext && (c.getContext('webgl') || c.getContext('webgl2') || c.getContext('experimental-webgl'));
      if (gl) return c;
    } catch (e) {}
  }
  canvases.sort((a, b) => (b.width * b.height) - (a.width * a.height));
  return canvases[0];
}

//地图截图工具按钮
function clearSelection() {
  selectState.hasSelection = false;
  selectState.points = [];
  selectState.geoPoints = null;
  selectState.drawing = false;
  selectState.currentPath = null;
  
  // 清除选区时保持控件隐藏
  setTimeout(() => {
    const layerItems = document.querySelectorAll('li.amap-ui-ctrl-layer-base-item');
    layerItems.forEach(item => {
      item.style.display = 'none';
    });
    
    const roadNetItems = document.querySelectorAll('li.amap-ui-ctrl-layer-overlay-item');
    roadNetItems.forEach(item => {
      const input = item.querySelector('input[data-id="AMap.TileLayer.RoadNet"]');
      if (input) {
        item.style.display = 'none';
      }
    });
  }, 100);

  redraw();
}

function enterSelectMode() {
  selectMode.value = true;
  try {
    const map = mapInstance.value;
    if (map && typeof map.setStatus === 'function') {
      map.setStatus({ dragEnable: false, scrollWheel: false, doubleClickZoom: false });
    }
  } catch (e) {}
  
  // 控件保持隐藏状态
  setTimeout(() => {
    const layerItems = document.querySelectorAll('li.amap-ui-ctrl-layer-base-item');
    layerItems.forEach(item => {
      item.style.display = 'none';
    });
    
    const roadNetItems = document.querySelectorAll('li.amap-ui-ctrl-layer-overlay-item');
    roadNetItems.forEach(item => {
      const input = item.querySelector('input[data-id="AMap.TileLayer.RoadNet"]');
      if (input) {
        item.style.display = 'none';
      }
    });
  }, 100);
  
  selectState.hasSelection = false; selectState.rect = null; selectState.geoRect = null;
  selectState.drawing = false;
  nextTick(() => resizeOverlayCanvas());
}

async function finishSelectMode() {
  selectMode.value = false;
  try {
    const map = mapInstance.value;
    if (map && typeof map.setStatus === 'function') {
      map.setStatus({ dragEnable: true, scrollWheel: true, doubleClickZoom: true });
    }
  } catch (e) {}
  
  console.log('完成选区模式，选区状态:', {
    hasSelection: selectState.hasSelection,
    geoPoints: selectState.geoPoints,
    pointsCount: selectState.geoPoints ? selectState.geoPoints.length : 0,
    drawing: selectState.drawing
  });
  
  // 显示地图类型控件和路网控件
  setTimeout(() => {
    const layerItems = document.querySelectorAll('li.amap-ui-ctrl-layer-base-item');
    layerItems.forEach(item => {
      item.style.display = 'block';
    });
    
    const roadNetItems = document.querySelectorAll('li.amap-ui-ctrl-layer-overlay-item');
    roadNetItems.forEach(item => {
      const input = item.querySelector('input[data-id="AMap.TileLayer.RoadNet"]');
      if (input) {
        item.style.display = 'block';
      }
    });
  }, 100);
  
  nextTick(() => {
    redraw();
  });
  
  // 自动保存大地图截图和基地选区截图
  try {
    messages.value.push({
      role: 'system', 
      text: '开始保存基地选区请稍后...' 
    });
    
    await autoSaveScreenshots();
    
    if (selectState.hasSelection && selectState.geoPoints && selectState.geoPoints.length >= 3) {
      console.log('检测到有效多边形选区，开始自动截取标准基底图...');
      await captureStandardBaseAutomatically();
    } else {
      console.log('无有效选区或选区点数不足，跳过标准基底图截取');
    }
  } catch (error) {
    console.error('自动保存过程出错:', error);
  }
}

//自动保存卫星地图截图工具
async function autoSaveScreenshots() {
  const map = mapInstance.value;
  
  return new Promise(async (resolve) => {
    const container = (typeof map.getContainer === 'function'
      ? map.getContainer()
      : document.getElementById('fudan-map'));

    const canvas = findMapCanvas(container);
    if (!canvas) {
      console.error('未找到地图 canvas，无法导出截图');
      resolve();
      return;
    }
    
    if (typeof canvas.toDataURL !== 'function') {
      console.error('浏览器不支持 canvas.toDataURL()');
      resolve();
      return;
    }

    // 导出整图作为大地图
    const bigImageBase64 = canvas.toDataURL('image/png');
    const isPolygonSelection = selectState.geoPoints && selectState.geoPoints.length > 0;

    
    console.log('截图信息:', {
      hasSelection: selectState.hasSelection,
      isPolygonSelection,
      polygonPointsCount: selectState.geoPoints ? selectState.geoPoints.length : 0
    });

    try {
      const bigResponse = await fetch('http://127.0.0.1:5000/save-screenshot', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          image: bigImageBase64,
          role: 'big',
          selection_type: isPolygonSelection ? 'polygon' : 'rectangle'
        })
      });

      // 如果没有选区，只保存大地图
      if (!selectState.hasSelection) {
        console.log('无选区，只保存大地图成功！');
        resolve();
        return;
      }

      //截取基地选区
      let smallImageBase64 = null;
      let smallData = {
        role: 'small',
        selection_type: isPolygonSelection ? 'polygon' : 'rectangle'
      };

      if (isPolygonSelection) {
        console.log('处理多边形选区截图...');
        
        // 获取多边形的屏幕坐标点
        const screenPoints = [];
        for (const geoPoint of selectState.geoPoints) {
          const screenPoint = lngLatToContainerPixel(geoPoint);
          if (screenPoint) {
            screenPoints.push({ x: screenPoint.x, y: screenPoint.y });
          }
        }
        
        if (screenPoints.length > 2) {
          smallImageBase64 = await cropPolygonImage(canvas, container, screenPoints);
          
          if (smallImageBase64) {
            // 计算多边形的边界框
            smallData.polygon_points = selectState.geoPoints; 
            smallData.polygon_screen_points = screenPoints;   
            const xs = screenPoints.map(p => p.x);
            const ys = screenPoints.map(p => p.y);
            const minX = Math.min(...xs);
            const maxX = Math.max(...xs);
            const minY = Math.min(...ys);
            const maxY = Math.max(...ys);
            smallData.bounding_box = {
              x: minX,
              y: minY,
              width: maxX - minX,
              height: maxY - minY
            };
            
            console.log('多边形裁剪成功，边界框:', smallData.bounding_box);
          } else {
            console.error('多边形裁剪失败');
          }
        } else {
          console.error('多边形点数不足，无法裁剪');
        }
        
      } 

      if (!smallImageBase64) {
        console.error('选区裁剪失败');
        resolve();
        return;
      }

      smallData.image = smallImageBase64;

      // 保存基地选区图
      const smallResponse = await fetch('http://127.0.0.1:5000/save-screenshot', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(smallData)
      });

      const bigResult = await bigResponse.json();
      const smallResult = await smallResponse.json();
      
      if (bigResult.ok && smallResult.ok) {
        console.log('截图自动保存成功！');
      } else {
        console.error('自动保存失败: ' + (bigResult.error || smallResult.error));
      }
    } catch (error) {
      console.error('自动保存截图时发生错误: ' + error.message);
    } finally {
      resolve();
    }
  });
}

//自动保存三维地图基地截图
async function captureStandardBaseAutomatically() {
  if (!selectState.hasSelection || !selectState.geoPoints) {
    console.log('没有有效选区，跳过标准基底图截取');
    return;
  }
  console.log('开始自动截取标准基底图流程...');
  
  try {
    const map = mapInstance.value;
    const AMap = AMapRef.value;

    // 保存当前地图状态
    const originalPitch = map.getPitch();
    const originalRotation = map.getRotation();
    console.log('保存当前地图状态:', { pitch: originalPitch, rotation: originalRotation });

    // 切换到标准图层
    await switchToStandardLayer();
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // 截取标准基底图
    console.log('开始截取标准基底图...');
    await captureStandardBaseSimple();
    
    // 设置pitch为0，等待8秒后截图
    console.log('设置pitch为0，准备截取顶视图...');
    map.setPitch(0);
    await new Promise(resolve => setTimeout(resolve, 8000));
    
    // 截取顶视图下的两张图
    await captureOverheadImages();
    
    // 恢复地图状态
    console.log('恢复地图状态...');
    map.setPitch(originalPitch);
    map.setRotation(originalRotation);
    await new Promise(resolve => setTimeout(resolve, 2000));
    await switchToSatelliteLayer();
    console.log('标准基底图自动截取流程完成！');
    
    messages.value.push({
      role: 'system',
      text: '基地选区保存完毕。'
    });
    
  } catch (error) {
    console.error('自动截取标准基底图失败:', error);
    messages.value.push({
      role: 'system',
      text: '基地选区保存失败: ' + error.message
    });
    
    try {
      await switchToSatelliteLayer();
    } catch (e) {
      console.error('切换回卫星图层失败:', e);
    }
  } finally {
    scrollToBottom();
  }
}

async function captureOverheadImages() {
  const map = mapInstance.value;
  
  return new Promise(async (resolve) => {
    const container = (typeof map.getContainer === 'function'
      ? map.getContainer()
      : document.getElementById('fudan-map'));

    const canvas = findMapCanvas(container);
    if (!canvas) {
      console.error('未找到地图 canvas，无法导出截图');
      resolve();
      return;
    }
    
    if (typeof canvas.toDataURL !== 'function') {
      console.error('浏览器不支持 canvas.toDataURL()');
      resolve();
      return;
    }

    // 导出整图作为大地图（big_over）
    const bigImageBase64 = canvas.toDataURL('image/png');
    const isPolygonSelection = selectState.geoPoints && selectState.geoPoints.length > 0;

    try {
      const bigResponse = await fetch('http://127.0.0.1:5000/save-screenshot', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          image: bigImageBase64,
          role: 'big_over',
          selection_type: isPolygonSelection ? 'polygon' : 'rectangle'
        })
      });

      // 如果没有选区，只保存大地图
      if (!selectState.hasSelection) {
        console.log('无选区，只保存大地图成功！');
        resolve();
        return;
      }

      // 截取基地选区（small_over）
      let smallImageBase64 = null;
      let smallData = {
        role: 'small_over',
        selection_type: isPolygonSelection ? 'polygon' : 'rectangle'
      };

      if (isPolygonSelection) {
        console.log('处理多边形选区截图（顶视图）...');
        
        // 获取多边形的屏幕坐标点
        const screenPoints = [];
        for (const geoPoint of selectState.geoPoints) {
          const screenPoint = lngLatToContainerPixel(geoPoint);
          if (screenPoint) {
            screenPoints.push({ x: screenPoint.x, y: screenPoint.y });
          }
        }
        
        if (screenPoints.length > 2) {
          smallImageBase64 = await cropPolygonImage(canvas, container, screenPoints);
          
          if (smallImageBase64) {
            // 计算多边形的边界框
            smallData.polygon_points = selectState.geoPoints; 
            smallData.polygon_screen_points = screenPoints;   
            const xs = screenPoints.map(p => p.x);
            const ys = screenPoints.map(p => p.y);
            const minX = Math.min(...xs);
            const maxX = Math.max(...xs);
            const minY = Math.min(...ys);
            const maxY = Math.max(...ys);
            smallData.bounding_box = {
              x: minX,
              y: minY,
              width: maxX - minX,
              height: maxY - minY
            };
            
            console.log('多边形裁剪成功（顶视图），边界框:', smallData.bounding_box);
          } else {
            console.error('多边形裁剪失败（顶视图）');
          }
        } else {
          console.error('多边形点数不足，无法裁剪（顶视图）');
        }
        
      } 

      if (!smallImageBase64) {
        console.error('选区裁剪失败（顶视图）');
        resolve();
        return;
      }

      smallData.image = smallImageBase64;

      // 保存基地选区图（small_over）
      const smallResponse = await fetch('http://127.0.0.1:5000/save-screenshot', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(smallData)
      });

      const bigResult = await bigResponse.json();
      const smallResult = await smallResponse.json();
      
      if (bigResult.ok && smallResult.ok) {
        console.log('顶视图截图自动保存成功！');
      } else {
        console.error('顶视图自动保存失败: ' + (bigResult.error || smallResult.error));
      }
    } catch (error) {
      console.error('自动保存顶视图截图时发生错误: ' + error.message);
    } finally {
      resolve();
    }
  });
}

//切换图层工具，使用html元素
function switchToStandardLayer() {
  return new Promise((resolve, reject) => {
    try {
      // 在切换图层时，保持路网控件的当前状态
      const layerItems = document.querySelectorAll('li.amap-ui-ctrl-layer-base-item');
      layerItems.forEach(item => {
        item.style.display = 'block';
      });
      
      setTimeout(() => {
        const standardLayerRadio = document.querySelector('li.amap-ui-ctrl-layer-base-item input[data-id="AMap.TileLayer"]');
        if (standardLayerRadio) {
          console.log('找到标准图层单选按钮，模拟点击...');
          standardLayerRadio.click();
          setTimeout(() => {
            console.log('已切换到标准图层');
            resolve();
          }, 1000);
        } else {
          reject(new Error('无法找到标准图层单选按钮'));
        }
      }, 100);
    } catch (error) {
      reject(error);
    }
  });
}

function switchToSatelliteLayer() {
  return new Promise((resolve, reject) => {
    try {
      // 在切换图层时，保持路网控件的当前状态
      const layerItems = document.querySelectorAll('li.amap-ui-ctrl-layer-base-item');
      layerItems.forEach(item => {
        item.style.display = 'block';
      });
      
      setTimeout(() => {
        const satelliteLayerRadio = document.querySelector('li.amap-ui-ctrl-layer-base-item input[data-id="AMap.TileLayer.Satellite"]');
        if (satelliteLayerRadio) {
          console.log('找到卫星图单选按钮，模拟点击...');
          satelliteLayerRadio.click();
          setTimeout(() => {
            console.log('已切换回卫星图');
            resolve();
          }, 1000);
        } else {
          reject(new Error('无法找到卫星图单选按钮'));
        }
      }, 100);
    } catch (error) {
      reject(error);
    }
  });
}


// 多边形裁剪函数
function cropPolygonImage(canvas, container, polygonPoints) {
  return new Promise((resolve) => {
    const img = new Image();
    img.src = canvas.toDataURL('image/png');

    img.onload = () => {
      const cssW = container.clientWidth;
      const cssH = container.clientHeight;
      const imgW = img.width;
      const imgH = img.height;
      const scaleX = imgW / cssW;
      const scaleY = imgH / cssH;
      
      // 计算多边形的边界框
      const xs = polygonPoints.map(p => p.x);
      const ys = polygonPoints.map(p => p.y);
      const minX = Math.min(...xs);
      const maxX = Math.max(...xs);
      const minY = Math.min(...ys);
      const maxY = Math.max(...ys);
      
      // 计算裁剪区域
      const sx = Math.round(minX * scaleX);
      const sy = Math.round(minY * scaleY);
      const sw = Math.round((maxX - minX) * scaleX);
      const sh = Math.round((maxY - minY) * scaleY);
      
      if (sw <= 0 || sh <= 0) {
        resolve(null);
        return;
      }

      // 创建裁剪画布
      const cutCanvas = document.createElement('canvas');
      cutCanvas.width = sw;
      cutCanvas.height = sh;
      const ctx = cutCanvas.getContext('2d');
      ctx.drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh);
      
      // 创建掩膜裁剪多边形区域
      const maskCanvas = document.createElement('canvas');
      maskCanvas.width = sw;
      maskCanvas.height = sh;
      const maskCtx = maskCanvas.getContext('2d');
      
      // 绘制多边形路径
      maskCtx.beginPath();
      const firstPoint = polygonPoints[0];
      maskCtx.moveTo(
        (firstPoint.x - minX) * scaleX,
        (firstPoint.y - minY) * scaleY
      );
      
      for (let i = 1; i < polygonPoints.length; i++) {
        const point = polygonPoints[i];
        maskCtx.lineTo(
          (point.x - minX) * scaleX,
          (point.y - minY) * scaleY
        );
      }
      maskCtx.closePath();
      maskCtx.clip();
      maskCtx.drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh);
      
      // 获取最终结果
      const selectionBase64 = maskCanvas.toDataURL('image/png');
      resolve(selectionBase64);
    };
    img.onerror = () => resolve(null);
  });
}

//标准图层截图函数
async function captureStandardBaseSimple() {
  if (!selectState.hasSelection || !selectState.geoPoints) {
    console.log('没有有效选区，跳过标准基底图截取');
    return;
  }
  console.log('开始截取标准基底图（最小外接矩形）...');
  
  try {
    const map = mapInstance.value;
    const AMap = AMapRef.value;
    if (!map || !AMap) {
      throw new Error('地图未初始化');
    }
    
    // 计算多边形区域在当前地图下的屏幕坐标
    console.log('计算多边形区域坐标...');
    const screenPoints = [];
    for (const geoPoint of selectState.geoPoints) {
      const screenPoint = lngLatToContainerPixel(geoPoint);
      if (screenPoint) {
        screenPoints.push({ x: screenPoint.x, y: screenPoint.y });
      }
    }
    
    if (screenPoints.length < 3) {
      throw new Error('无法获取有效的屏幕坐标点');
    }
    
    // 计算最小外接矩形
    const xs = screenPoints.map(p => p.x);
    const ys = screenPoints.map(p => p.y);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    
    const rect = {
      x: minX,
      y: minY,
      w: maxX - minX,
      h: maxY - minY
    };
    
    // 截取标准基底图
    const container = map.getContainer ? map.getContainer() : document.getElementById('fudan-map');
    const canvas = findMapCanvas(container);
    const standardBaseImage = await cropImage(canvas, container, rect);
    if (!standardBaseImage) {
      throw new Error('矩形裁剪失败');
    }
    
    // 发送到后端保存，明确标识为standard_base
    const response = await fetch('http://127.0.0.1:5000/save-screenshot', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        image: standardBaseImage,
        role: 'standard_base',  // 明确标识角色
        selection_type: 'rectangle', 
        bounding_box: rect, 
        polygon_points: selectState.geoPoints, 
        polygon_screen_points: screenPoints  
      })
    });
    
    const result = await response.json();
    if (result.ok) {
      console.log('标准基底图保存成功！');
    } else {
      throw new Error(result.error || '保存失败');
    }
    
  } catch (error) {
    console.error('截取标准基底图失败:', error);
    throw error; 
  }
}



//---------------------------------------------------------------------------------
//-----------------------------------调研报告分析设计-------------------------------
//---------------------------------------------------------------------------------

// 触发文件选择
function summarizeReport() {
  fileInput.value.click();
}

// 调研报告分析
async function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  
  if (!file.name.endsWith('.docx')) {
    alert('请选择docx文件');
    return;
  }
  messages.value.push({ 
    role: 'system', 
    text: '总结处理调研报告中请稍后...' 
  });
  scrollToBottom();
  isUploadingReport.value = true;
  try {
    const formData = new FormData();
    formData.append('docx', file);
    
    const response = await fetch('http://127.0.0.1:5000/summarize-report', {
      method: 'POST',
      body: formData
    });
    
    const result = await response.json();
    if (result.ok) {
      try {

        // 解析后端返回的JSON数据
        const responseData = typeof result.summary === 'string' ? JSON.parse(result.summary) : result.summary;
        let contentText = '';
        if (responseData.choices && responseData.choices[0] && responseData.choices[0].message) {
          contentText = responseData.choices[0].message.content;
        } else {
          contentText = '无法解析返回的数据结构';
        }
        messages.value.push({ 
          role: 'system', 
          text: contentText 
        });
        
        // 保存调研报告总结内容
        surveySummary.value = contentText;
      } 

      catch (error) {
        messages.value.push({ 
          role: 'system', 
          text: '数据处理错误: ' + error.message 
        });
      }
    } else {
      messages.value.push({ 
        role: 'system', 
        text: '总结失败: ' + result.error 
      });
    }
  } catch (error) {
    messages.value.push({ 
      role: 'system', 
      text: '上传文件时发生错误: ' + error.message 
    });
  } finally {
    isUploadingReport.value = false;
    event.target.value = '';
    scrollToBottom();
  }
}



//---------------------------------------------------------------------------------
//-----------------------------------AI助手分析-------------------------------------
//---------------------------------------------------------------------------------


// 对话窗口部分
function sendMessage() {
  const txt = (newMessage.value || '').trim();
  if (!txt) return;
  
  // 风格建议模式
  if (isWaitingForStyleSuggestion.value) {
    handleStyleSuggestion(txt);
    return;
  }
  
  // 修改建议模式
  if (isEditingSuggestion.value) {
    handleSuggestionRequest(txt);
    return;
  }

  // 普通对话逻辑
  messages.value.push({ role: 'user', text: txt });
  setTimeout(() => {
    messages.value.push({ role: 'system', text: '已收到：' + txt });
    scrollToBottom(); 
  }, 300);
  newMessage.value = '';
  scrollToBottom(); 
}


// AI助手分析工具函数
async function analyzeWithAI() {
  if (!selectState.hasSelection) {
    alert('请先选择区域并保存截图！');
    return;
  }
  
  // 等待用户输入风格建议的状态
  isWaitingForStyleSuggestion.value = true;
  let promptText = '请输入您对本次规划的风格建议，然后点击发送。';
  messages.value.push({ 
    role: 'system', 
    text: promptText 
  });
  scrollToBottom();
}

async function handleStyleSuggestion(styleSuggestion) {
  try {
    messages.value.push({ role: 'user', text: `风格建议：${styleSuggestion}` });
    newMessage.value = '';
    isWaitingForStyleSuggestion.value = false;  
    
    // 获取技术经济指标数据
    console.log("开始获取技术经济指标数据...");
    const indicatorsSuccess = await fetchEconomicIndicators();
    
    // 将经济指标转换为通用字符串格式
    let economicIndicatorsStr = '';
    if (economicIndicators.value) {
      console.log("经济指标数据获取成功:", economicIndicators.value);
      economicIndicatorsStr = Object.entries(economicIndicators.value)
        .map(([key, value]) => {
          const formattedKey = key.split('_').map(word => 
            word.charAt(0).toUpperCase() + word.slice(1)
          ).join(' ');
          return `${formattedKey}: ${value}`;
        })
        .join('\n');
    } else {
      console.log("经济指标数据为空");
    }
    
    // 准备街景图分析结果
    const streetViewAnalyses = streetViewAnalysisResults.value || [];
    
    // 调试信息
    console.log("=== 发送的数据 ===");
    console.log("风格建议:", styleSuggestion);
    console.log("调研总结:", surveySummary.value);
    console.log("经济指标字符串:", economicIndicatorsStr);
    console.log("街景图分析结果:", streetViewAnalyses);
    console.log("===================");
    
    // 发送分析请求（添加street_view_analyses参数）
    const response = await fetch('http://127.0.0.1:5000/analyze-with-ai', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        style_suggestion: styleSuggestion,  
        survey_summary: surveySummary.value,
        economic_indicators_str: economicIndicatorsStr,
        street_view_analyses: streetViewAnalyses  // 新增：传递街景图分析结果
      })
    });
    
    const result = await response.json(); 
    if (result.ok) {
      messages.value.push({ 
        role: 'system', 
        text: 'AI分析建议：\n' + result.analysis 
      });
    } else {
      messages.value.push({ 
        role: 'system', 
        text: 'AI分析失败: ' + result.error 
      });
    }
    scrollToBottom(); 
  } catch (error) {
    messages.value.push({ 
      role: 'system', 
      text: 'AI分析时发生错误: ' + error.message 
    });
    scrollToBottom();
  }
}


//---------------------------------------------------------------------------------
//-----------------------------------草图生成设计-----------------------------------
//---------------------------------------------------------------------------------

//草图生成工具函数（普通版）
async function generateSketch() {
  await generateSketchInternal(false);
}

//草图生成工具函数（增强版，暂时还没用到）
async function generateSketchPro() {
  await generateSketchInternal(true);
}

async function generateSketchInternal(usePro = false) {
  if (!selectState.hasSelection) {
    alert('请先选择区域并保存截图！');
    return;
  }
  
  try {
    // 自动进行总结生图prompt
    let latestAnalysis = null;
    for (let i = messages.value.length - 1; i >= 0; i--) {
      const msg = messages.value[i];
      if (msg.role === 'system' && msg.text.includes('AI分析建议')) {
        latestAnalysis = msg.text.replace('AI分析建议：\n', '');
        break;
      }
    }
    
    messages.value.push({ 
      role: 'system', 
      text: '正在总结生图提示词，请稍候...' 
    });
    scrollToBottom();
    
    let latestSummarizedPrompt = null;
    
    try {
      const response = await fetch('http://127.0.0.1:5000/summarize-prompt', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          analysis: latestAnalysis
        })
      });
      
      const result = await response.json();
      if (result.ok) {
        let contentText = result.summarized_prompt;
        const promptMatch = contentText.match(/总结的prompt为：(.+)/);
        if (promptMatch && promptMatch[1]) {
          latestSummarizedPrompt = promptMatch[1].trim();
        } else {
          latestSummarizedPrompt = contentText;
        }
        
        messages.value.push({ 
          role: 'system', 
          text: '总结的提示词：' + latestSummarizedPrompt 
        });
      } else {
        throw new Error(result.error || '总结失败');
      }
    } catch (error) {
      console.error('总结生图提示词失败:', error);
      messages.value.push({ 
        role: 'system', 
        text: '总结提示词失败: ' + error.message 
      });
      scrollToBottom();
      return;
    }
    
    messages.value = messages.value.filter(msg => 
      !msg.text.includes('正在总结生图提示词，请稍后……')
    );
    
    // 使用总结后的prompt调用草图生成接口，传递pro参数
    messages.value.push({ 
      role: 'system', 
      text: `正在生成城市规划草图${usePro ? '（增强版）' : ''}，请稍候...` 
    });
    scrollToBottom();
    
    const response = await fetch('http://127.0.0.1:5000/generate-sketch', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        prompt: latestSummarizedPrompt,
        pro: usePro
      })
    });
    
    const result = await response.json();
    messages.value = messages.value.filter(msg => 
      !msg.text.includes('正在生成城市规划草图，请稍后……')
    );
    
    if (result.ok && result.images && result.images.length > 0) {
      // 将生成的图片添加到三维渲染图集
      imageCollections.value.sketch.images = result.images;
      imageCollections.value.sketch.currentIndex = 0;
      imageCollections.value.sketch.history = result.images.map(image => [image]);
      imageCollections.value.sketch.currentHistoryIndex = result.images.map(() => 0);
      currentCollectionType.value = 'sketch';
      currentPage.value = 'image-collection';
      hasGeneratedImage.value = true;
      messages.value.push({ 
        role: 'system', 
        text: `城市规划草图${usePro ? '（增强版）' : ''}生成成功！` 
      });      
    } else {
      messages.value.push({ 
        role: 'system', 
        text: `草图${usePro ? '（增强版）' : ''}生成失败: ` + (result.error || '未知错误') 
      });
    }
  } catch (error) {
    messages.value.push({ 
      role: 'system', 
      text: `生成草图${usePro ? '（增强版）' : ''}时发生错误: ` + error.message 
    });
  } finally {
    scrollToBottom();
  }
}

function onImageLoad() {
  console.log('图片加载成功');
}

// 显示图片集函数
function showImageCollection() {
  const hasImages = imageCollections.value.sketch.images.length > 0 || 
                   imageCollections.value.zoning.images.length > 0;
  
  if (hasImages) {
    currentPage.value = 'image-collection';
  } else {
    messages.value.push({
      role: 'system',
      text: '暂无生成的图片，请先生成图片'
    });
    scrollToBottom();
  }
}



//---------------------------------------------------------------------------------
//-----------------------------------草图修改设计-----------------------------------
//---------------------------------------------------------------------------------

//草图修改建议工具函数
function suggestEdits() {
  if (generatedImages.value.length === 0) {
    alert('请先生成草图才能使用修改建议功能！');
    return;
  }
  isWaitingForStyleSuggestion.value = false;
  isEditingSuggestion.value = true;
  
  messages.value.push({ 
    role: 'system', 
    text: '请输入您对当前草图的修改意见，然后点击发送。' 
  });
  scrollToBottom();
}

async function handleSuggestionRequest(suggestionText) {
  if (!currentGeneratedImage.value) {
    alert('当前没有可修改的草图');
    return;
  }
  
  try {
    isEditingSuggestion.value = false;
    messages.value.push({ role: 'user', text: `修改建议：${suggestionText}` });
    newMessage.value = '';
    messages.value.push({ role: 'system', text: '正在根据您的建议修改草图，请稍候...' });
    scrollToBottom();
    
    const response = await fetch('http://127.0.0.1:5000/suggest-edits', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        prompt: suggestionText,
        reference_image: currentGeneratedImage.value
      })
    });
    
    const result = await response.json();
    messages.value = messages.value.filter(msg => 
      !msg.text.includes('正在根据您的建议修改草图')
    );
    
    if (result.ok && result.images && result.images.length > 0) {
      const currentImgIndex = currentImageIndex.value;
      const modifiedImage = result.images[0];
      
      // 如果当前图片没有历史记录，先添加原始图片
      if (!imageHistory.value[currentImgIndex]) {
        imageHistory.value[currentImgIndex] = [];
      }
      if (imageHistory.value[currentImgIndex].length === 0) {
        const originalImage = generatedImages.value[currentImgIndex];
        imageHistory.value[currentImgIndex].push(originalImage);
        currentHistoryIndex.value[currentImgIndex] = 0;
      }
      
      // 添加修改后的图片到历史记录
      imageHistory.value[currentImgIndex].push(modifiedImage);
      currentHistoryIndex.value[currentImgIndex] = imageHistory.value[currentImgIndex].length - 1;
      messages.value.push({ role: 'system', text: '修改建议已生成新草图！' });
      console.log('添加修改记录:', {
        图片索引: currentImgIndex,
        新历史索引: currentHistoryIndex.value[currentImgIndex],
        历史记录长度: imageHistory.value[currentImgIndex].length
      });
    } 
    else {
      messages.value.push({ role: 'system', text: '修改建议生成失败: ' + (result.error || '未知错误') });
    }
  } catch (error) {
    messages.value.push({ role: 'system', text: '修改建议时发生错误: ' + error.message });
  } finally {
    isEditingSuggestion.value = false; 
    scrollToBottom();
  }
}

function scrollToBottom() {
  nextTick(() => {
    const chatWindow = document.querySelector('.chat-window');
    if (chatWindow) {
      chatWindow.scrollTop = chatWindow.scrollHeight;
    }
  });
}

// 图片加载失败尝试重新加载
function onImageError(event) {
  console.error('图片加载失败:', event);
  const img = event.target;
  setTimeout(() => {
    const currentImage = getCurrentImage();
    if (currentImage) {
      img.src = currentImage + '?t=' + new Date().getTime();
    }
  }, 500);
}



//---------------------------------------------------------------------------------
//-----------------------------------平面图生成设计---------------------------------
//---------------------------------------------------------------------------------


async function generateZoningPrompt() {
  try {
    isGeneratingZoningPrompt.value = true;
    
    // 获取最新的AI分析结果
    let latestAnalysis = null;
    for (let i = messages.value.length - 1; i >= 0; i--) {
      const msg = messages.value[i];
      if (msg.role === 'system' && msg.text.includes('AI分析建议')) {
        latestAnalysis = msg.text.replace('AI分析建议：\n', '');
        break;
      }
    }
    
    if (!latestAnalysis) {
      messages.value.push({ 
        role: 'system', 
        text: '请先进行AI分析再生成功能分区图' 
      });
      scrollToBottom();
      return;
    }
    
    messages.value.push({ 
      role: 'system', 
      text: '正在生成功能分区布局分析，请稍候...' 
    });
    scrollToBottom();
    
    // 调用后端生成功能分区总结
    const promptResponse = await fetch('http://127.0.0.1:5000/generate-zoning-prompt', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        analysis: latestAnalysis
      })
    });
    const promptResult = await promptResponse.json();
    messages.value = messages.value.filter(msg => 
      !msg.text.includes('正在生成功能分区布局分析，请稍候...')
    );
    
    if (!promptResult.ok || !promptResult.zoning_prompt) {
      messages.value.push({ 
        role: 'system', 
        text: '功能分区分析失败: ' + (promptResult.error || '未知错误') 
      });
      scrollToBottom();
      return;
    }
    
    let contentText = promptResult.zoning_prompt;
    const promptMatch = contentText.match(/总结的prompt为：(.+)/);
    if (promptMatch && promptMatch[1]) {
      contentText = promptMatch[1].trim();
    }
    
    // 打印功能分区方案到对话窗口
    messages.value.push({ 
      role: 'system', 
      text: `📋 **功能分区方案总结完成**\n\n${contentText}` 
    });
    scrollToBottom();
    

    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // 自动调用生成功能分区图
    messages.value.push({ 
      role: 'system', 
      text: '正在基于功能分区方案生成功能分区图...' 
    });
    scrollToBottom();
    
    const sketchResponse = await fetch('http://127.0.0.1:5000/generate-zoning-sketch', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        content_text: contentText
      })
    });
    
    const sketchResult = await sketchResponse.json();
    messages.value = messages.value.filter(msg => 
      !msg.text.includes('正在基于功能分区方案生成功能分区图...')
    );
    
    if (sketchResult.ok && sketchResult.images && sketchResult.images.length > 0) {
      // 将生成的功能分区图添加到功能分区图集
      imageCollections.value.zoning.images.push(sketchResult.images[0]);
      imageCollections.value.zoning.currentIndex = imageCollections.value.zoning.images.length - 1;
      
      // 初始化历史记录
      if (!imageCollections.value.zoning.history[imageCollections.value.zoning.currentIndex]) {
        imageCollections.value.zoning.history[imageCollections.value.zoning.currentIndex] = [];
      }
      imageCollections.value.zoning.history[imageCollections.value.zoning.currentIndex].push(sketchResult.images[0]);
      imageCollections.value.zoning.currentHistoryIndex[imageCollections.value.zoning.currentIndex] = 0;
      
      // 设置当前显示的功能分区图集
      currentCollectionType.value = 'zoning';
      currentPage.value = 'image-collection';
      hasGeneratedImage.value = true;
      messages.value.push({ 
        role: 'system', 
        text: '✅ 功能分区图生成成功！' 
      });
      
    } else {
      messages.value.push({ 
        role: 'system', 
        text: '功能分区图生成失败: ' + (sketchResult.error || '未知错误') 
      });
    }
    
  } catch (error) {
    messages.value.push({ 
      role: 'system', 
      text: '生成功能分区图时发生错误: ' + error.message 
    });
  } finally {
    isGeneratingZoningPrompt.value = false;
    scrollToBottom();
  }
}


//---------------------------------------------------------------------------------
//-----------------------------------图片展示部分-----------------------------------
//---------------------------------------------------------------------------------


// 进入具体图片集
function enterCollection(collectionType) {
  if (imageCollections.value[collectionType].images.length === 0) {
    messages.value.push({
      role: 'system',
      text: `暂无${collectionType === 'sketch' ? '三维渲染图' : '功能分区图'}，请先生成图片`
    });
    return;
  }
  
  currentCollectionType.value = collectionType;
  currentPage.value = 'image';
  hasGeneratedImage.value = true;
}

// 返回图片集选择页面
function backToCollection() {
  currentPage.value = 'image-collection';
  hasGeneratedImage.value = true;
}

// 获取当前图片集
function getCurrentCollection() {
  return imageCollections.value[currentCollectionType.value] || { images: [], currentIndex: 0, history: [], currentHistoryIndex: [] };
}

// 获取当前图片
function getCurrentImage() {
  const collection = getCurrentCollection();
  if (collection.images.length > 0 && collection.currentIndex < collection.images.length) {
    const historyIndex = collection.currentHistoryIndex[collection.currentIndex] || 0;
    let imageUrl = collection.history[collection.currentIndex]?.[historyIndex] || '';
    if (imageUrl && !imageUrl.startsWith('http')) {
      imageUrl = 'http://127.0.0.1:5000' + imageUrl;
    }
    return imageUrl;
  }
  return '';
}

// 检查是否可以撤回
function canRevertEdit() {
  const collection = getCurrentCollection();
  return collection.history[collection.currentIndex] && 
         collection.currentHistoryIndex[collection.currentIndex] > 0;
}

// 检查是否可以回到修改
function canRestoreEdit() {
  const collection = getCurrentCollection();
  return collection.history[collection.currentIndex] && 
         collection.currentHistoryIndex[collection.currentIndex] < collection.history[collection.currentIndex].length - 1;
}

// 翻页函数
function nextImage() {
  const collection = getCurrentCollection();
  if (collection.currentIndex < collection.images.length - 1) {
    collection.currentIndex++;
  }
}

function prevImage() {
  const collection = getCurrentCollection();
  if (collection.currentIndex > 0) {
    collection.currentIndex--;
  }
}

// 历史记录函数
function revertEdit() {
  const collection = getCurrentCollection();
  if (collection.history[collection.currentIndex] && collection.currentHistoryIndex[collection.currentIndex] > 0) {
    collection.currentHistoryIndex[collection.currentIndex]--;
  }
}

function restoreEdit() {
  const collection = getCurrentCollection();
  const maxIndex = collection.history[collection.currentIndex].length - 1;
  if (collection.currentHistoryIndex[collection.currentIndex] < maxIndex) {
    collection.currentHistoryIndex[collection.currentIndex]++;
  }
}

// 页面切换函数
function togglePage() {
  if (currentPage.value === 'image') {
    // 从图片页面返回图片集选择页面
    currentPage.value = 'image-collection';
  } else if (currentPage.value === 'image-collection') {
    // 从图片集选择页面返回地图
    currentPage.value = 'map';
    hasGeneratedImage.value = imageCollections.value.sketch.images.length > 0 || 
                            imageCollections.value.zoning.images.length > 0;
  } else {
    // 从地图进入图片集选择页面
    const hasImages = imageCollections.value.sketch.images.length > 0 || 
                     imageCollections.value.zoning.images.length > 0;
    
    if (hasImages) {
      currentPage.value = 'image-collection';
      hasGeneratedImage.value = true;
    } else {
      messages.value.push({
        role: 'system',
        text: '暂无生成的图片，请先生成图片'
      });
    }
  }
}

</script>


<style scoped>

@import './style.css';

</style>
