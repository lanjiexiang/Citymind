<template>
  <div id="app" class="app-root">
    <header class="app-header">
      <div class="header-left">
        <div class="logo">🏙 CiityMind</div>
      </div>
      
      <!-- 工具栏按钮 -->
      <div class="header-center">
        <div class="toolbar-dropdown" ref="toolbarDropdownRef">
          <button class="btn toolbar-btn dropdown-trigger" @click.stop="toggleToolbar">
            <span class="btn-text">工具栏（待完善）</span>
            <span class="dropdown-arrow" :class="{ 'rotated': showToolbar }">▼</span>
          </button>
          
          <div class="dropdown-menu" v-show="showToolbar" @click.stop>
            <button class="btn toolbar-btn" @click="handleToolbarAction('summarizeReport')">
              <span class="btn-icon">📄</span>
              <span class="btn-text">调研分析</span>
            </button>
            <button class="btn toolbar-btn" @click="handleToolbarAction('analyzeStreetViews')">
                <span class="btn-icon">🌆</span>
                <span class="btn-text">街景图分析</span>
            </button>

            <button class="btn toolbar-btn" @click="handleToolbarAction('analyzeWithAI')">
              <span class="btn-icon">🤖</span>
              <span class="btn-text">AI规划分析</span>
            </button>
            <button class="btn toolbar-btn" @click="handleToolbarAction('generateSketch')">
              <span class="btn-icon">✨</span>
              <span class="btn-text">三维草图</span>
            </button>

            <button class="btn toolbar-btn" @click="handleToolbarAction('generateZoningPrompt')">
              <span class="btn-icon">✨</span>
              <span class="btn-text">功能分区图</span>
            </button>

            <button class="btn toolbar-btn" @click="handleToolbarAction('generateStreamMap')">
              <span class="btn-icon">✨</span>
              <span class="btn-text">流线图</span>
            </button>

            <button class="btn toolbar-btn" @click="handleToolbarAction('generateEffectView')">
                <span class="btn-icon">✨</span>
                <span class="btn-text">效果图</span>
            </button>

            <button class="btn toolbar-btn" @click="handleToolbarAction('suggestEdits')">
              <span class="btn-icon">✏️</span>
              <span class="btn-text">修改草图（维修中）</span>
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- 左侧AI助手栏 -->
    <div class="app-main" style="display:flex; gap:12px; padding:12px;">

      <aside class="left-panel" style="width:360px; height: calc(100vh - 80px);">
        <div class="panel-title">
          AI助手小blue
          <span class="status-indicator-right">
            <span class="status-dot"></span>
            <span class="status-text">在线</span>
          </span>
        </div>
        <div 
          class="chat-window" 
          :style="{
            overflowY: 'auto', 
            flex: showChatInput ? '1' : '1 1 auto',
            minHeight: '0', 
            marginBottom: '8px',
            height: showChatInput ? 'calc(100% - 80px)' : '100%'
          }"
        >
          <div v-for="(m, idx) in messages" :key="idx" class="chat-msg" :class="{'from-user': m.role === 'user', 'from-system': m.role !== 'user'}">
            <div class="msg-content">{{ m.text }}</div>
          </div>
        </div>
        <div class="chat-input" v-show="showChatInput" style="margin-top:8px; margin-bottom:15px; flex-shrink: 0;">
          <textarea 
            v-model="newMessage" 
            @keydown.enter.exact.prevent="sendMessage" 
            placeholder="输入消息并按 Enter 发送" 
            style="width:100%;min-height:56px; margin-bottom:8px;"
            ref="chatTextarea"
          ></textarea>
          <button class="btn" @click="sendMessage" style="width:100%;">发送</button>
        </div>
      </aside>

    <!-- 右侧集成区域 -->
    <section class="center-panel" style="flex:1; display:flex; flex-direction:column;">
      <div class="map-top" style="margin-bottom:8px;" v-show="currentPage === 'map'">
        <div class="btn-group" style="margin-left: auto; display: flex; gap: 8px; align-items: center;">
          <!-- 非选择模式：显示选择按钮 -->
          <button class="btn map-control-btn" v-if="!selectMode && !hasGeneratedImage" @click="enterSelectMode">选择基地轮廓</button>
          
         <template v-if="selectMode">
          <!-- 识别中状态提示 -->
          <span v-if="contourState.isProcessing" class="processing-hint" style="color: #409EFF; margin-right: 10px;">
            正在识别轮廓...
          </span>
          
          <!-- 步骤2：确认紫色轮廓（识别完成后显示） -->
          <template v-if="contourState.isShowingContours && !cadState.purpleContoursConfirmed">
            <button class="btn map-control-btn" 
                    v-if="contourState.selectedIndices.size > 0"
                    @click="confirmPurpleContours"
                    style="background: #E6A23C;">
              确认基地轮廓 ({{ contourState.selectedIndices.size }})
            </button>
            
            <!-- 重新进入选择模式按钮（替代原来的重新识别） -->
            <button class="btn map-control-btn" 
                    @click="restartSelectMode"
                    style="background: #F56C6C;">
              重新选择
            </button>
            
            <!-- 上传用地红线图按钮（禁用状态） -->
            <button class="btn map-control-btn" 
                    disabled
                    style="background: #9E9E9E; opacity: 0.6; cursor: not-allowed;"
                    title="请先确认基地轮廓">
              📐 上传用地红线图
            </button>
          </template>
          
          <!-- 步骤3：紫色轮廓已确认，可以上传用地红线图 -->
          <template v-else-if="cadState.purpleContoursConfirmed">
            <button v-if="!cadState.isLoaded"
                    class="btn map-control-btn" 
                    @click="triggerCADUpload"
                    style="background: #67C23A;">
              📐 上传用地红线图
            </button>
          </template>
          
          <!-- 退出选择模式 -->
          <button class="btn map-control-btn" @click="exitSelectMode">
            退出
          </button>
        </template>
          
          <!-- 当有生成图片时显示查看图片集按钮 -->
          <button 
            class="btn map-control-btn" 
            @click="showImageCollection"
            v-if="hasGeneratedImage"
            style="background: var(--accent-2); margin-left: 8px;"
          >
            <span class="btn-text">查看图片集</span>
          </button>
        </div>
        
        <!-- 选择模式状态提示 -->
        <div v-if="selectMode" class="contour-status" style="margin-top: 8px; font-size: 12px; color: #666;">
          {{ contourState.statusText }}
          <span v-if="contourState.isShowingContours" style="margin-left: 10px; color: #409EFF;">
            提示：点击轮廓选择/取消
          </span>
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
          
          <!-- 基地轮廓覆盖层Canvas -->
          <canvas
            ref="overlayCanvas"
            :style="{ position: 'absolute', left:0, top:0, width:'100%', height:'100%', pointerEvents: 'none' }"
          ></canvas>
          
          <!-- 预览截图区域框 -->
          <div 
            ref="previewRect"
            v-show="contourState.isPreviewing && selectMode"
            class="preview-rect"
            :style="previewRectStyle"
          ></div>
          
          <!-- 轮廓识别结果Canvas（用于选择紫色轮廓） -->
          <canvas
            ref="contourCanvas"
            v-show="contourState.isShowingContours && selectMode"
            :style="contourCanvasStyle"
            @click="handleContourClick"
          ></canvas>

          <!-- CAD 红线叠加组件 -->
          <CADOverlay
            v-if="selectMode"
            ref="cadOverlayRef"
            :map-instance="mapInstance"
            :amap="AMapRef"
            :select-mode="selectMode"
            :capture-rect="contourState.captureRect || defaultCaptureRect"
            :detected-contours="getSelectedPurpleContours()"
            :auto-match-enabled="cadState.purpleContoursConfirmed"
            @cad-confirmed="handleCADConfirmed"
            @cad-cleared="handleCADCleared"
            @cad-loaded="handleCADLoaded"
          />
          
            <!-- 街景图上传框 -->
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
          
          <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:15px; justify-content:center; align-items:center; max-width:1000px; width:100%;">

            <!-- 鸟瞰图集卡片 -->
            <div 
              class="collection-card" 
              @click="enterCollection('bird_view')"
              :style="{
                opacity: imageCollections.bird_view.images.length > 0 ? 1 : 0.6,
                cursor: imageCollections.bird_view.images.length > 0 ? 'pointer' : 'not-allowed'
              }"
            >
              <div class="card-icon">🦅</div>
              <h3>鸟瞰图</h3>
              <p>{{ imageCollections.bird_view.images.length }} 张图片</p>
              <div v-if="imageCollections.bird_view.images.length === 0" style="color:#999; font-size:12px;">
                暂无图片
              </div>
            </div>
            
            <!-- 平视图集卡片 -->
            <div 
              class="collection-card" 
              @click="enterCollection('flat_view')"
              :style="{
                opacity: imageCollections.flat_view.images.length > 0 ? 1 : 0.6,
                cursor: imageCollections.flat_view.images.length > 0 ? 'pointer' : 'not-allowed'
              }"
            >
              <div class="card-icon">🏙️</div>
              <h3>平视图</h3>
              <p>{{ imageCollections.flat_view.images.length }} 张图片</p>
              <div v-if="imageCollections.flat_view.images.length === 0" style="color:#999; font-size:12px;">
                暂无图片
              </div>
            </div>
            
            <!-- 顶视图集卡片 -->
            <div 
              class="collection-card" 
              @click="enterCollection('top_view')"
              :style="{
                opacity: imageCollections.top_view.images.length > 0 ? 1 : 0.6,
                cursor: imageCollections.top_view.images.length > 0 ? 'pointer' : 'not-allowed'
              }"
            >
              <div class="card-icon">📐</div>
              <h3>顶视图</h3>
              <p>{{ imageCollections.top_view.images.length }} 张图片</p>
              <div v-if="imageCollections.top_view.images.length === 0" style="color:#999; font-size:12px;">
                暂无图片
              </div>
            </div>
            
            <!-- 流线图集卡片 -->
            <div 
              class="collection-card" 
              @click="enterCollection('stream_map')"
              :style="{
                opacity: imageCollections.stream_map.images.length > 0 ? 1 : 0.6,
                cursor: imageCollections.stream_map.images.length > 0 ? 'pointer' : 'not-allowed'
              }"
            >
              <div class="card-icon">🔄</div>
              <h3>流线图</h3>
              <p>{{ imageCollections.stream_map.images.length }} 张图片</p>
              <div v-if="imageCollections.stream_map.images.length === 0" style="color:#999; font-size:12px;">
                暂无图片
              </div>
            </div>

            <!-- 效果图集卡片 -->
            <div 
              class="collection-card" 
              @click="enterCollection('effect_view')"
              :style="{
                opacity: imageCollections.effect_view.images.length > 0 ? 1 : 0.6,
                cursor: imageCollections.effect_view.images.length > 0 ? 'pointer' : 'not-allowed'
              }"
            >
              <div class="card-icon">🎨</div>
              <h3>效果图</h3>
              <p>{{ imageCollections.effect_view.images.length }} 张图片</p>
              <div v-if="imageCollections.effect_view.images.length === 0" style="color:#999; font-size:12px;">
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
              <h3>功能分区图</h3>
              <p>{{ imageCollections.zoning.images.length }} 张图片</p>
              <div v-if="imageCollections.zoning.images.length === 0" style="color:#999; font-size:12px;">
                暂无图片
              </div>
            </div>
          </div>

          <button class="btn" @click="togglePage" style="margin-top:30px; padding:10px 20px;">
            返回地图
          </button>
        </div>

        <!-- 具体图片集浏览页面 -->
        <div v-show="currentPage === 'image'" class="image-wrapper" style="width:100%; height:100%; display:flex; flex-direction:column; justify-content:flex-start; align-items:center; background:#f0f0f0; overflow:hidden;">
          <div style="width:100%; padding:8px 16px; background:white; border-bottom:1px solid #e0e0e0; display:flex; align-items:center; flex-shrink:0; min-height:50px;">
            <button class="btn" @click="backToCollection" style="display:flex; align-items:center; gap:6px; margin-right: auto;">
              ← 返回图片集
            </button>
            <div style="display:flex; align-items:center; gap:12px; position: absolute; left: 50%; transform: translateX(-50%);">
              <span style="font-weight:bold; font-size:16px; text-align: center;">
                {{ getCollectionTitle() }}
              </span>
              <div v-if="getCurrentCollection().images.length > 1" style="display: flex; align-items: center; gap: 8px; font-size:14px; color:#666;">
                <span>图片 {{ getCurrentCollection().currentIndex + 1 }}/{{ getCurrentCollection().images.length }}</span>
              </div>
            </div>
          </div>
          <div style="flex:1; width:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:0; overflow:auto; position:relative;">
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
            <div v-if="getCurrentImage()" style="max-width:95%; max-height:95%; display:flex; justify-content:center; align-items:center; padding:20px;">
              <img 
                :src="getCurrentImage()" 
                :alt="getCollectionTitle()" 
                style="max-width:100%; max-height:100%; object-fit:contain; transition: all 0.3s ease; box-shadow: 0 4px 12px rgba(0,0,0,0.15); border-radius:4px;"
                @load="onImageLoad"
                @error="onImageError"
              >
            </div>
            
            <!-- 图片历史记录控制 -->
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

  <!-- 街景图查看模态框 -->
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
        
        <!-- 问题描述输入区域 -->
        <div class="problem-description-section">
          <h4>问题描述</h4>
          <textarea 
            v-model="problemDescription" 
            placeholder="请输入关于此处街景图存在问题的描述..."
            class="problem-description-textarea"
            :disabled="isSavingProblem"
          ></textarea>
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

  <!-- 隐藏的本地文件上传 -->
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







<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, computed} from 'vue';
import CADOverlay from './components/CADOverlay.vue';

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
const toolbarDropdownRef = ref(null);
const hiddenMapStyle = [
  {
    "featureType": "all",
    "elementType": "labels",
    "stylers": [{"visibility": "off"}]
  },
  {
    "featureType": "road",
    "elementType": "all", 
    "stylers": [{"visibility": "off"}]
  },
  {
    "featureType": "road",
    "elementType": "labels",
    "stylers": [{"visibility": "off"}]
  },
  {
    "featureType": "traffic",
    "elementType": "all",
    "stylers": [{"visibility": "off"}]
  },
  {
    "featureType": "traffic", 
    "elementType": "labels",
    "stylers": [{"visibility": "off"}]
  },
  {
    "featureType": "poi",
    "elementType": "labels",
    "stylers": [{"visibility": "off"}]
  },
  {
    "featureType": "administrative",
    "elementType": "labels",
    "stylers": [{"visibility": "off"}]
  }
];


// CAD组件引用
const cadOverlayRef = ref(null);
const contourCanvas = ref(null);
// 轮廓识别相关状态
const contourState = reactive({
  isPreviewing: false,           // 是否正在预览截图区域
  isProcessing: false,           // 是否正在处理识别
  isShowingContours: false,      // 是否正在显示识别到的轮廓
  statusText: '点击"预览区域"开始选择基地轮廓',
  captureRect: null,             // 截图区域信息
  captureMapState: null,         // 截图时的地图状态
  allPolygons: [],               // 所有识别到的轮廓
  selectedIndices: new Set(),    // 选中的轮廓索引
  savedBasePolygons: [],         // 保存的基地轮廓（经纬度坐标）
  baseMapPolygons: [],           // 高德地图 Polygon 覆盖物
  captureWidth: 1200,             // 截图宽度
  captureHeight: 600             // 截图高度
});

// CAD状态管理
const cadState = reactive({
  isLoaded: false,               // DXF文件是否已加载
  purpleContoursConfirmed: false // 紫色轮廓是否已确认
});

// 轮廓颜色配置
const contourColors = {
  purple: { fill: 'rgba(128,0,128,0.4)', stroke: '#800080' },
  green: { fill: 'rgba(0,128,0,0.4)', stroke: '#008000' },
  blue: { fill: 'rgba(0,0,255,0.4)', stroke: '#0000FF' },
  pink: { fill: 'rgba(255,105,180,0.4)', stroke: '#FF69B4' },
  default: { fill: 'rgba(255,0,0,0.4)', stroke: '#FF0000' },
  selected: { fill: 'rgba(255,215,0,0.6)', stroke: '#FFD700' },
  base: { fill: 'rgba(0,255,255,0.5)', stroke: '#00FFFF' }
};


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
const showChatInput = ref(false);
const activeFunction = ref(''); 


// 草图生成相关
const imageCollections = ref({
  bird_view: { 
    images: [],
    currentIndex: 0,
    history: [],
    currentHistoryIndex: []
  },
  flat_view: { 
    images: [],
    currentIndex: 0,
    history: [],
    currentHistoryIndex: []
  },
  top_view: { 
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
  },
  stream_map: { 
    images: [],
    currentIndex: 0,
    history: [],
    currentHistoryIndex: []
  },
  effect_view: { 
    images: [],
    currentIndex: 0,
    history: [],
    currentHistoryIndex: []
  }
});
const currentCollectionType = ref(null); 
const currentPage = ref('map');

const isGeneratingZoningPrompt = ref(false);
const isGeneratingEffectView = ref(false);



//---------------------------------------------------------------------------------
//-----------------------------------computed模块-----------------------------------
//---------------------------------------------------------------------------------

const hasGeneratedImage = computed(() => {
  return imageCollections.value.bird_view.images.length > 0 || 
         imageCollections.value.flat_view.images.length > 0 || 
         imageCollections.value.top_view.images.length > 0 ||
         imageCollections.value.zoning.images.length > 0 ||
         imageCollections.value.stream_map.images.length > 0 ||
         imageCollections.value.effect_view.images.length > 0; 
});

// 预览框样式计算属性
const previewRectStyle = computed(() => {
  if (!contourState.captureRect) return { display: 'none' };
  const { left, top, width, height } = contourState.captureRect;
  return {
    position: 'absolute',
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    height: `${height}px`,
    border: '2px dashed #409EFF',
    background: 'rgba(64, 158, 255, 0.1)',
    zIndex: 999,
    pointerEvents: 'none'
  };
});

// 轮廓Canvas样式计算属性
const contourCanvasStyle = computed(() => {
  if (!contourState.captureRect) return { display: 'none' };
  const { left, top, width, height } = contourState.captureRect;
  return {
    position: 'absolute',
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    height: `${height}px`,
    zIndex: 1001,
    cursor: 'pointer',
    pointerEvents: 'auto'
  };
});

// CAD模式下的默认截图区域
const defaultCaptureRect = computed(() => {
  const map = mapInstance.value;
  const container = map?.getContainer?.();
  if (!container) {
    return { left: 100, top: 100, width: contourState.captureWidth, height: contourState.captureHeight };
  }
  const rect = container.getBoundingClientRect();
  const width = contourState.captureWidth;
  const height = contourState.captureHeight;
  return {
    left: (rect.width - width) / 2,
    top: (rect.height - height) / 2,
    width,
    height,
    containerRect: rect
  };
});

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
    rotation: 0,
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
    
    // 修改：初始隐藏整个图层控件容器
    setTimeout(() => {
      const layerList = document.querySelector('.amap-ctrl-list-layer');
      if (layerList) {
        //layerList.style.display = 'none';
      }
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
  
  if (!map || !AMap || !llObj) {
    console.error('地图实例或坐标对象为空');
    return null;
  }
  
  try {
    // 验证经纬度值的有效性
    const lng = parseFloat(llObj.lng);
    const lat = parseFloat(llObj.lat);
    
    if (isNaN(lng) || isNaN(lat)) {
      console.error('坐标值包含NaN:', { lng: llObj.lng, lat: llObj.lat });
      return null;
    }
    
    // 检查经纬度范围
    if (lng < -180 || lng > 180 || lat < -90 || lat > 90) {
      console.error('坐标范围无效:', { lng, lat });
      return null;
    }
    
    const lnglat = new AMap.LngLat(lng, lat);
    if (!lnglat) {
      console.error('创建LngLat对象失败');
      return null;
    }
    
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
  document.addEventListener('click', handleClickOutside);
});

onBeforeUnmount(() => {
  if (mapInstance.value) {
    try { mapInstance.value.destroy && mapInstance.value.destroy(); } catch(e){}
    mapInstance.value = null;
  }
  window.removeEventListener('resize', resizeOverlayCanvas);
  document.removeEventListener('click', handleClickOutside);
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

// 简字段名格式化
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

// 点击工具栏切换显示/隐藏
function toggleToolbar() {
  showToolbar.value = !showToolbar.value;
}

function handleToolbarAction(action) {
  showToolbar.value = false;
  
  switch (action) {
    case 'summarizeReport':
      summarizeReport();
      break;
    case 'analyzeStreetViews':
      analyzeStreetViews();
      break;
    case 'analyzeWithAI':
      analyzeWithAI();
      break;
    case 'generateSketch':
      generateSketch();
      break;
    case 'generateZoningPrompt':
      generateZoningPrompt();
      break;
    case 'suggestEdits':
      suggestEdits();
      break;
    case 'generateStreamMap': 
      generateStreamMap();
      break;
    case 'generateEffectView':
      generateEffectView();
      break;
    default:
      console.warn('未知的工具栏动作:', action);
  }
}

// 点击页面其他区域关闭下拉菜单
function handleClickOutside(event) {
  if (toolbarDropdownRef.value && !toolbarDropdownRef.value.contains(event.target)) {
    showToolbar.value = false;
  }
}




//---------------------------------------------------------------------------------
//-----------------------------------CAD选区---------------------------------------
//---------------------------------------------------------------------------------
// ============= 轮廓识别核心函数 =============

// 进入选择模式 - 切换到bg二维地图
function enterSelectMode() {
  // ===== 新增：先自动切换到标准图层 =====
  try {
    // 先显示图层控件容器（确保可以点击）
    const layerList = document.querySelector('.amap-ctrl-list-layer');
    if (layerList) {
      layerList.style.display = 'block';
    }
    
    // 点击标准图层单选按钮
    const standardLayerRadio = document.querySelector('li.amap-ui-ctrl-layer-base-item input[data-id="AMap.TileLayer"]');
    if (standardLayerRadio) {
      console.log('自动切换到标准图层...');
      standardLayerRadio.click();
    } else {
      console.warn('未找到标准图层单选按钮');
    }
  } catch (e) {
    console.error('自动切换标准图层失败:', e);
  }
  // ===== 新增结束 =====
  selectMode.value = true;
  
  const map = mapInstance.value;
  const AMap = AMapRef.value;
  
  try {
    // 保存当前地图状态
    window._savedMapState = {
      pitch: map.getPitch ? map.getPitch() : 0,
      rotation: map.getRotation ? map.getRotation() : 0,
      zoom: map.getZoom(),
      center: map.getCenter()
    };
    
    // 保存进入选择模式前的覆盖物数量
    window._savedBasePolygonsCount = contourState.savedBasePolygons.length;
    
    // 隐藏已确认的基地轮廓覆盖物
    contourState.baseMapPolygons.forEach(p => {
      if (p.hide) p.hide();
    });
    
    // 设置地图为2D模式，只显示bg（用于轮廓识别）
    map.setPitch(0);
    map.setRotation(0);
    
    // 切换到只有bg的地图模式
    map.setFeatures(['bg']);
    map.setLabelzIndex && map.setLabelzIndex(-1);
    
    // 禁用地图交互（允许缩放和平移以调整区域）
    if (map && typeof map.setStatus === 'function') {
      map.setStatus({ 
        dragEnable: true, 
        scrollWheel: true, 
        doubleClickZoom: false,
        rotateEnable: false,
        pitchEnable: false
      });
    }
  } catch (e) {
    console.error('切换地图模式失败:', e);
  }
  
  // 隐藏地图类型控件
  setTimeout(() => {
    const layerItems = document.querySelectorAll('li.amap-ui-ctrl-layer-base-item');
    layerItems.forEach(item => {
      //item.style.display = 'none';
    });
    
    const roadNetItems = document.querySelectorAll('li.amap-ui-ctrl-layer-overlay-item');
    roadNetItems.forEach(item => {
      //item.style.display = 'none';
    });
  }, 100);
  
  // 重置轮廓状态
  contourState.isPreviewing = true;
  contourState.isProcessing = false;
  contourState.isShowingContours = false;
  contourState.statusText = '正在自动识别基地轮廓，请稍候...';
  contourState.captureRect = defaultCaptureRect.value; 
  contourState.allPolygons = [];
  contourState.selectedIndices = new Set();
  
  // 重置CAD状态
  cadState.isLoaded = false;
  cadState.purpleContoursConfirmed = false;
  
  messages.value.push({
    role: 'system',
    text: '已进入基地轮廓选择模式，正在自动识别轮廓...'
  });
  scrollToBottom();
  
  // 自动执行识别流程
  nextTick(() => {
    setTimeout(() => {
      autoRecognizeContours();
    }, 500); // 给地图一点时间稳定
  });
}

// 自动执行轮廓识别流程（合并预览+识别+显示结果）
async function autoRecognizeContours() {
  if (!contourState.captureRect) {
    contourState.statusText = '截图区域设置失败';
    return;
  }
  
  contourState.isProcessing = true;
  contourState.statusText = '正在自动截取地图并识别轮廓...';
  
  try {
    // 等待地图渲染稳定
    await new Promise(resolve => setTimeout(resolve, 800));
    
    const dataURL = captureContourMapArea();
    
    const response = await fetch('http://127.0.0.1:5000/process-contour', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image: dataURL,
        width: contourState.captureRect.width,
        height: contourState.captureRect.height,
        role: 'contour_extraction'
      })
    });
    
    if (!response.ok) throw new Error(`HTTP错误: ${response.status}`);
    const result = await response.json();
    if (!result.ok) throw new Error(result.error || '处理失败');
    
    if (result.polygons?.length > 0) {
      contourState.allPolygons = processContourPolygons(result.polygons);
      contourState.selectedIndices = new Set();
      drawAllContours();
      contourState.isShowingContours = true;
      contourState.statusText = `成功识别 ${contourState.allPolygons.length} 个轮廓，请点击选择基地轮廓`;
      
      messages.value.push({
        role: 'system',
        text: `已自动识别到 ${contourState.allPolygons.length} 个轮廓，请点击选择基地的轮廓，然后点击"确认基地轮廓"。`
      });
    } else {
      contourState.statusText = '未检测到轮廓，请调整地图位置后重新进入选择模式';
      messages.value.push({
        role: 'system',
        text: '未检测到轮廓，请调整地图位置后重新尝试。'
      });
    }
    
  } catch (error) {
    console.error('自动轮廓识别失败:', error);
    contourState.statusText = `识别失败: ${error.message}`;
    messages.value.push({
      role: 'system',
      text: `轮廓识别失败: ${error.message}`
    });
  } finally {
    contourState.isProcessing = false;
    scrollToBottom();
  }
}

// 截取地图区域（只截取bg图层）
function captureContourMapArea() {
  const map = mapInstance.value;
  const { left, top, width, height } = contourState.captureRect;
  
  // 截图前临时隐藏基地轮廓
  contourState.baseMapPolygons.forEach(p => p.hide && p.hide());
  
  const mapContainer = map.getContainer();
  const canvases = mapContainer.querySelectorAll('canvas');
  
  if (canvases.length === 0) {
    throw new Error('无法找到地图canvas元素');
  }
  
  const tempCanvas = document.createElement('canvas');
  tempCanvas.width = width;
  tempCanvas.height = height;
  const tempCtx = tempCanvas.getContext('2d');
  
  canvases.forEach(sourceCanvas => {
    if (sourceCanvas.width === 0 || sourceCanvas.height === 0) return;
    try {
      const scaleX = sourceCanvas.width / mapContainer.offsetWidth;
      const scaleY = sourceCanvas.height / mapContainer.offsetHeight;
      tempCtx.drawImage(
        sourceCanvas,
        left * scaleX, top * scaleY,
        width * scaleX, height * scaleY,
        0, 0, width, height
      );
    } catch (e) {
      console.warn('Canvas图层绘制失败:', e);
    }
  });
  
  // 恢复基地轮廓显示
  contourState.baseMapPolygons.forEach(p => p.show && p.show());
  
  return tempCanvas.toDataURL('image/png');
}


// 处理轮廓坐标，转换为像素坐标
function processContourPolygons(polygons) {
  const { width, height } = contourState.captureRect;
  return polygons.map((poly, index) => {
    const coords = poly.coordinates || poly.contour || [];
    const pixelCoords = coords.map(point => {
      let x, y;
      if (Array.isArray(point)) {
        x = point[0] <= 1 ? point[0] * width : point[0];
        y = point[1] <= 1 ? point[1] * height : point[1];
      } else if (point.x !== undefined) {
        x = point.x <= 1 ? point.x * width : point.x;
        y = point.y <= 1 ? point.y * height : point.y;
      }
      return { x, y };
    });
    return { index, type: poly.type || 'default', coords: pixelCoords };
  });
}

// 绘制所有轮廓到Canvas
function drawAllContours() {
  const canvas = contourCanvas.value;
  if (!canvas || !contourState.captureRect) return;
  
  const { width, height } = contourState.captureRect;
  
  canvas.width = width;
  canvas.height = height;
  
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, width, height);
  
  contourState.allPolygons.forEach(poly => {
    const isSelected = contourState.selectedIndices.has(poly.index);
    const color = isSelected ? contourColors.selected : (contourColors[poly.type] || contourColors.default);
    
    ctx.fillStyle = color.fill;
    ctx.strokeStyle = color.stroke;
    ctx.lineWidth = isSelected ? 3 : 2;
    
    ctx.beginPath();
    poly.coords.forEach((point, i) => {
      ctx[i === 0 ? 'moveTo' : 'lineTo'](point.x, point.y);
    });
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  });
}

// 检测点击位置是否在多边形内
function isPointInContourPolygon(x, y, coords) {
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

// 处理轮廓Canvas点击
function handleContourClick(e) {
  if (!contourState.isShowingContours) return;
  
  const canvas = contourCanvas.value;
  const rect = canvas.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  
  let clickedIndex = -1;
  for (let i = contourState.allPolygons.length - 1; i >= 0; i--) {
    if (isPointInContourPolygon(x, y, contourState.allPolygons[i].coords)) {
      clickedIndex = i;
      break;
    }
  }
  
  if (clickedIndex === -1) return;
  
  if (e.shiftKey) {
    contourState.selectedIndices.add(clickedIndex);
  } else if (e.ctrlKey || e.metaKey) {
    contourState.selectedIndices.delete(clickedIndex);
  } else {
    if (contourState.selectedIndices.has(clickedIndex)) {
      contourState.selectedIndices.delete(clickedIndex);
    } else {
      contourState.selectedIndices.add(clickedIndex);
    }
  }
  
  drawAllContours();
  contourState.statusText = `已选择 ${contourState.selectedIndices.size} 个轮廓`;
}

// 像素坐标转经纬度
function contourPixelToLngLat(pixelCoords) {
  const map = mapInstance.value;
  const AMap = AMapRef.value;
  const { left, top } = contourState.captureRect;
  
  return pixelCoords.map(point => {
    const pixel = new AMap.Pixel(left + point.x, top + point.y);
    const lngLat = map.containerToLngLat(pixel);
    return [lngLat.lng, lngLat.lat];
  });
}

// 确认紫色轮廓（用于匹配）
function confirmPurpleContours() {
  if (contourState.selectedIndices.size === 0) {
    contourState.statusText = '请先选择紫色轮廓';
    return;
  }
  
  // 标记紫色轮廓已确认
  cadState.purpleContoursConfirmed = true;
  
  // 提示用户可以上传用地红线图
  contourState.statusText = `已确认基地轮廓，请上传用地红线图进行匹配`;
}

// 获取选中的紫色轮廓
function getSelectedPurpleContours() {
  if (contourState.selectedIndices.size === 0) return [];
  return contourState.allPolygons.filter(p => contourState.selectedIndices.has(p.index));
}

// 触发CAD文件上传
function triggerCADUpload() {
  console.log('点击上传按钮，cadOverlayRef:', cadOverlayRef.value);
  if (cadOverlayRef.value) {
    cadOverlayRef.value.triggerFileUpload();
  } else {
    console.warn('CADOverlay组件引用未准备好，请稍后再试');
    // 延迟重试
    setTimeout(() => {
      if (cadOverlayRef.value) {
        cadOverlayRef.value.triggerFileUpload();
      }
    }, 100);
  }
}

// CAD 模式：确认后的事件处理
function handleCADConfirmed(data) {
  const { polygons } = data || {};
  if (!polygons || !Array.isArray(polygons) || polygons.length === 0) {
    contourState.statusText = '未从 CAD 文件中获得有效红线轮廓';
    return;
  }

  contourState.savedBasePolygons = polygons.map(p => ({
    type: p.type || 'redline',
    coords: p.pixelCoords,
    lngLatCoords: p.lngLatCoords
  }));

  if (contourState.savedBasePolygons.length > 0) {
    const allGeoPoints = [];
    contourState.savedBasePolygons.forEach(poly => {
      poly.lngLatCoords.forEach(coord => {
        allGeoPoints.push({ lng: coord[0], lat: coord[1] });
      });
    });
    selectState.geoPoints = allGeoPoints;
    selectState.hasSelection = true;
  }

  createBaseMapPolygons();
  contourState.statusText = `已从 CAD 文件保存 ${contourState.savedBasePolygons.length} 个基地轮廓`;
  scrollToBottom();

  // 走统一的退出与截图流程
  finishSelectModeAndSave();
}

function handleCADCleared() {
  cadState.isLoaded = false;
  cadState.purpleContoursConfirmed = false;
  messages.value.push({
    role: 'system',
    text: '已清除上传的 CAD 用地红线图'
  });
  scrollToBottom();
}

// CAD文件加载完成
function handleCADLoaded() {
  cadState.isLoaded = true;
  contourState.statusText = 'DXF文件已加载，正在自动匹配轮廓...';
}

// 创建高德地图Polygon覆盖物
function createBaseMapPolygons() {
  const map = mapInstance.value;
  const AMap = AMapRef.value;
  
  // 先移除已有的
  removeBaseMapPolygons();
  
  contourState.savedBasePolygons.forEach(poly => {
    const polygon = new AMap.Polygon({
      path: poly.lngLatCoords,
      fillColor: contourColors.base.stroke,
      strokeColor: contourColors.base.stroke,
      strokeWeight: 3,
      fillOpacity: 0.3,
      strokeOpacity: 1
    });
    contourState.baseMapPolygons.push(polygon);
    map.add(polygon);
    
    // 如果在选择模式下，隐藏新创建的覆盖物（直到确认并退出选择模式）
    if (selectMode.value) {
      polygon.hide();
    }
  });
}

// 移除高德地图Polygon覆盖物
function removeBaseMapPolygons() {
  const map = mapInstance.value;
  if (!map) return;
  
  contourState.baseMapPolygons.forEach(polygon => {
    map.remove(polygon);
  });
  contourState.baseMapPolygons = [];
}

// 重新进入选择模式（替代原来的 clearContours + 重新识别流程）
function restartSelectMode() {
  // 清除当前识别结果
  const canvas = contourCanvas.value;
  if (canvas) {
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }
  
  // 重置状态
  contourState.isShowingContours = false;
  contourState.allPolygons = [];
  contourState.selectedIndices = new Set();
  
  // 隐藏已确认的基地轮廓覆盖物
  contourState.baseMapPolygons.forEach(p => {
    if (p.hide) p.hide();
  });
  
  // 重新自动识别
  contourState.statusText = '正在重新识别...';
  autoRecognizeContours();
}

// 完成选择模式并保存截图
async function finishSelectModeAndSave() {
  // 先退出选择模式，恢复正常地图
  selectMode.value = false;
  
  const map = mapInstance.value;
  
  try {
    // 恢复地图交互
    if (map && typeof map.setStatus === 'function') {
      map.setStatus({ 
        dragEnable: true, 
        scrollWheel: true, 
        doubleClickZoom: true,
        rotateEnable: true,
        pitchEnable: true
      });
    }
    
    // ===== 修改：设置 pitch 为 35 度（不是恢复原来的）=====
    map.setPitch(40);
    map.setRotation(window._savedMapState?.rotation || -30);
    
    // 恢复所有地图要素
    map.setFeatures(['bg', 'road', 'building', 'point']);
    
  } catch (e) {
    console.error('恢复地图模式失败:', e);
  }
  
  // 显示地图类型控件
  setTimeout(() => {
    const layerItems = document.querySelectorAll('li.amap-ui-ctrl-layer-base-item');
    layerItems.forEach(item => {
      item.style.display = 'block';
    });
  }, 100);
  
  contourState.isPreviewing = false;
  
  // 等待地图恢复
  await new Promise(resolve => setTimeout(resolve, 2000));
  
  // 重绘已保存的基地轮廓到overlayCanvas
  redrawBasePolygons();
  
  // ===== 修改：新的截图流程 =====
  try {
    messages.value.push({
      role: 'system', 
      text: '开始保存基地选区截图...' 
    });
    scrollToBottom();
    
    // 步骤1：点击卫星图按钮，保存 big 和 small
    await clickSatelliteLayer();
    await new Promise(resolve => setTimeout(resolve, 1500)); // 等待图层切换
    
    await saveBigAndSmallScreenshots();  // ← 保存 big 和 small
    
    // 步骤2：点击标准图层按钮，保存 standard_base
    await clickStandardLayer();
    await new Promise(resolve => setTimeout(resolve, 1500)); // 等待图层切换
    
    await saveStandardBaseScreenshot();  // ← 保存 standard_base
    
    // 步骤3：设置 pitch 为 0，保存 big_over 和 small_over（原有逻辑）
    console.log('设置pitch为0，准备截取顶视图...');
    map.setPitch(0);
    await new Promise(resolve => setTimeout(resolve, 8000));
    
    await captureOverheadImages();  // ← 保存 big_over 和 small_over（原有函数）
    
    // 恢复地图状态
    console.log('恢复地图状态...');
    map.setPitch(40);  
    map.setRotation(window._savedMapState?.rotation || -30);
    await new Promise(resolve => setTimeout(resolve, 2000));
    await clickSatelliteLayer();  // ← 切回卫星图
    
    messages.value.push({
      role: 'system',
      text: '基地选区保存完成！'
    });
    scrollToBottom();
    
  } catch (error) {
    console.error('自动保存过程出错:', error);
    messages.value.push({
      role: 'system',
      text: '保存截图时出错: ' + error.message
    });
    scrollToBottom();
  }
}

// 点击卫星图按钮
async function clickSatelliteLayer() {
  return new Promise((resolve, reject) => {
    try {
      // 显示图层控件容器
      const layerList = document.querySelector('.amap-ctrl-list-layer');
      if (layerList) {
        layerList.style.display = 'block';
      }
      
      setTimeout(() => {
        const satelliteLayerRadio = document.querySelector('li.amap-ui-ctrl-layer-base-item input[data-id="AMap.TileLayer.Satellite"]');
        if (satelliteLayerRadio) {
          console.log('点击卫星图按钮...');
          satelliteLayerRadio.click();
          setTimeout(() => {
            console.log('已切换到卫星图');
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

// 点击标准图层按钮
async function clickStandardLayer() {
  return new Promise((resolve, reject) => {
    try {
      // 显示图层控件容器
      const layerList = document.querySelector('.amap-ctrl-list-layer');
      if (layerList) {
        layerList.style.display = 'block';
      }
      
      setTimeout(() => {
        const standardLayerRadio = document.querySelector('li.amap-ui-ctrl-layer-base-item input[data-id="AMap.TileLayer"]');
        if (standardLayerRadio) {
          console.log('点击标准图层按钮...');
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


// 保存 big 和 small 截图（卫星图，pitch=35）
async function saveBigAndSmallScreenshots() {
  const map = mapInstance.value;
  
  return new Promise(async (resolve) => {
    const container = (typeof map.getContainer === 'function'
      ? map.getContainer()
      : document.getElementById('fudan-map'));

    const canvas = findMapCanvas(container);
    if (!canvas) {
      console.error('未找到地图 canvas');
      resolve();
      return;
    }

    // 导出整图作为大地图
    const bigImageBase64 = canvas.toDataURL('image/png');
    const isPolygonSelection = selectState.geoPoints && selectState.geoPoints.length > 0;

    try {
      // 保存 big（卫星图全景，pitch=35）
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

      if (!selectState.hasSelection) {
        console.log('无选区，只保存大地图成功！');
        resolve();
        return;
      }

      // 截取基地选区 small
      let smallImageBase64 = null;
      let smallData = {
        role: 'small',
        selection_type: isPolygonSelection ? 'polygon' : 'rectangle'
      };

      if (isPolygonSelection) {
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
          }
        }
      }

      if (!smallImageBase64) {
        console.error('选区裁剪失败');
        resolve();
        return;
      }

      smallData.image = smallImageBase64;

      // 保存 small（卫星图选区，pitch=35）
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
        console.log('big 和 small 截图保存成功！');
      } else {
        console.error('保存失败:', bigResult.error || smallResult.error);
      }
    } catch (error) {
      console.error('保存 big/small 时发生错误:', error.message);
    } finally {
      resolve();
    }
  });
}

// 保存 standard_base 截图（标准图层，pitch=35）
async function saveStandardBaseScreenshot() {
  if (!selectState.hasSelection || !selectState.geoPoints) {
    console.log('没有有效选区，跳过 standard_base 截取');
    return;
  }
  
  console.log('开始截取 standard_base（标准图层，pitch=35）...');
  
  try {
    const map = mapInstance.value;
    const AMap = AMapRef.value;
    if (!map || !AMap) {
      throw new Error('地图未初始化');
    }
    map.setPitch(40);
    map.setRotation(0);
    // 等待地图状态稳定
    await new Promise(resolve => setTimeout(resolve, 1000));
    // 计算多边形区域屏幕坐标
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
    
    // 截图
    const container = map.getContainer ? map.getContainer() : document.getElementById('fudan-map');
    const canvas = findMapCanvas(container);
    const standardBaseImage = await cropRectangleImage(canvas, container, rect);
    
    if (!standardBaseImage) {
      throw new Error('矩形裁剪失败');
    }
    
    // 保存 standard_base
    const response = await fetch('http://127.0.0.1:5000/save-screenshot', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        image: standardBaseImage,
        role: 'standard_base',
        selection_type: 'rectangle',
        bounding_box: rect,
        polygon_points: selectState.geoPoints,
        polygon_screen_points: screenPoints
      })
    });
    
    const result = await response.json();
    if (result.ok) {
      console.log('standard_base 保存成功！');
    } else {
      throw new Error(result.error || '保存失败');
    }
    
  } catch (error) {
    console.error('截取 standard_base 失败:', error);
    throw error;
  }
}

// 重绘已保存的基地轮廓到overlayCanvas
function redrawBasePolygons() {
  const ctx = getCanvasCtx();
  const c = overlayCanvas.value;
  if (!ctx || !c) return;
  
  const cssW = c.clientWidth, cssH = c.clientHeight;
  ctx.clearRect(0, 0, cssW, cssH);
  
  // 绘制已保存的基地轮廓
  if (contourState.savedBasePolygons && contourState.savedBasePolygons.length > 0) {
    contourState.savedBasePolygons.forEach(poly => {
      const screenPoints = [];
      poly.lngLatCoords.forEach(coord => {
        const screenPoint = lngLatToContainerPixel({ lng: coord[0], lat: coord[1] });
        if (screenPoint) {
          screenPoints.push(screenPoint);
        }
      });
      
      if (screenPoints.length > 1) {
        ctx.save();
        ctx.beginPath();
        ctx.moveTo(screenPoints[0].x, screenPoints[0].y);
        for (let i = 1; i < screenPoints.length; i++) {
          ctx.lineTo(screenPoints[i].x, screenPoints[i].y);
        }
        ctx.closePath();
        
        ctx.fillStyle = 'rgba(0, 255, 255, 0.15)';
        ctx.fill();
        ctx.strokeStyle = '#00FFFF';
        ctx.lineWidth = 3;
        ctx.stroke();
        ctx.restore();
      }
    });
  }
}

// 修改原有的 redraw 函数
function redraw() {
  redrawBasePolygons();
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
    markerDiv.style.cssText = `
      width: 30px;
      height: 30px;
      position: relative;
      cursor: pointer;
    `;
    const dot = markerDiv.querySelector('.breathing-dot');
    if (dot) {
      dot.style.background = '#ff0000'; 
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
        id: markerId,
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

// 关闭街景图查看模态框
function closeStreetViewModal() {
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

// 处理街景图文件上传 
async function handleStreetViewUpload(event) {
  const file = event.target.files[0];
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
      const success = convertToPermanentBreathingMarker(
        streetViewPosition.value.marker, 
        result.image_url, 
        streetViewPosition.value.position
      );
      
      if (success) {
        //自动打开街景图查看模态框
        showStreetViewImage(result.image_url, streetViewPosition.value.position, Date.now());
        
        messages.value.push({
          role: 'system',
          text: '街景图上传成功，长按删除。请输入该处街景图的问题描述……'
        });
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

// 将临时呼吸点标记转换为永久呼吸点标记
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
      id: Date.now() + Math.random(), 
      isPermanent: true 
    });
    
    // 长按相关变量
    let longPressTimer = null;
    let isLongPress = false;
    
    // 添加鼠标按下事件 
    tempMarker.off('mousedown');
    tempMarker.on('mousedown', function(event) {
      event && event.stopPropagation && event.stopPropagation();
      isLongPress = false;
      longPressTimer = setTimeout(() => {
        isLongPress = true;
        showDeleteConfirmation(tempMarker, imageUrl, position);
      }, 800); // 800毫秒长按触发
    });
    
    // 添加鼠标抬起事件
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
    
    // 添加鼠标移出事件取消长按
    tempMarker.off('mouseout');
    tempMarker.on('mouseout', function(event) {
      if (longPressTimer) {
        clearTimeout(longPressTimer);
        longPressTimer = null;
      }
      isLongPress = false;
    });
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
          dot.style.background = '#ff0000'; 
          dot.style.boxShadow = '0 0 10px #ff0000'; 
        }
      }
    });
    
    tempMarker.on('mouseout', function() {
      const markerElement = tempMarker.getContent();
      if (markerElement && markerElement.style) {
        markerElement.style.transform = 'scale(1)';
        // 恢复呼吸点样式
        const dot = markerElement.querySelector('.breathing-dot');
        if (dot) {
          dot.style.background = '#ff0000'; 
          dot.style.boxShadow = 'none';
        }
      }
    });
    tempMarker.setTitle('街景图查看点（点击查看，长按删除）');
    
    // 保存到全局标记数组）
    if (!window.streetViewMarkers) {
      window.streetViewMarkers = [];
    }
    window.streetViewMarkers.push({
      marker: tempMarker,
      imageUrl: imageUrl,
      position: position,
      timestamp: Date.now(),
      isBreathingStyle: true 
    });
    
    console.log('临时呼吸点标记已转换为永久标记，当前标记数量:', window.streetViewMarkers.length);
    console.log('标记详细信息:', {
      imageUrl: imageUrl,
      position: position,
      marker: tempMarker,
      style: 'breathing_red' 
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

// 保存街景图问题描述
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


// 取消问题描述函数
function cancelProblemDescription() {
  // 恢复原来的问题描述
  if (currentStreetViewImage.value && streetViewProblemRecords.value[currentStreetViewImage.value]) {
    problemDescription.value = streetViewProblemRecords.value[currentStreetViewImage.value];
  } else {
    problemDescription.value = '';
  }
  
  // 清空保存状态
  saveProblemStatus.value = null;

}


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

//带呼吸点的地图截图
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
        
        // 关键修改：等待地图完全渲染后再截图
        setTimeout(() => {
            captureMapWithMarkers(container, keepMarker).then(dataURL => {
                // 安全地恢复标记可见状态
                if (hideOtherMarkers) {
                    safeRestoreMarkerVisibility(originalVisibility);
                }
                resolve(dataURL);
            }).catch(error => {
                console.error('截图失败:', error);
                if (hideOtherMarkers) {
                    safeRestoreMarkerVisibility(originalVisibility);
                }
                resolve(null);
            });
        }, 500); // 增加延迟确保地图状态稳定
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
  try {
    // 获取容器和画布的边界信息
    const containerRect = container.getBoundingClientRect();
    const mapRect = mapCanvas.getBoundingClientRect();
    if (!containerRect && !mapRect) {
      console.warn('drawMarkerToCanvas: 找不到容器边界信息，跳过绘制');
      return;
    }

    // 获取标记的经纬度位置
    const position = marker.getPosition();
    if (!position) {
      console.warn('drawMarkerToCanvas: 无法获取标记位置');
      return;
    }

    // 关键修改：使用更精确的坐标转换方法
    const pixelPos = lngLatToContainerPixel({ lng: position.lng, lat: position.lat });
    if (!pixelPos) {
      console.warn('drawMarkerToCanvas: 无法转换标记位置为像素坐标');
      return;
    }

    // 计算相对于地图容器的精确位置
    const mapContainer = document.getElementById('fudan-map');
    const mapContainerRect = mapContainer.getBoundingClientRect();
    
    // 计算标记在canvas上的精确位置
    const scaleX = mapCanvas.width / mapContainerRect.width;
    const scaleY = mapCanvas.height / mapContainerRect.height;
    
    const drawX = (pixelPos.x - mapContainerRect.left + containerRect.left) * scaleX;
    const drawY = (pixelPos.y - mapContainerRect.top + containerRect.top) * scaleY;

    // 获取标记的DOM元素和尺寸
    const markerContent = marker.getContent();
    const markerRect = markerContent ? markerContent.getBoundingClientRect() : null;
    
    const width = markerRect ? markerRect.width * scaleX : 30 * scaleX;
    const height = markerRect ? markerRect.height * scaleY : 30 * scaleY;
    const offsetX = Math.round(width / 2);
    const offsetY = Math.round(height / 2);

    const finalX = Math.round(drawX - offsetX);
    const finalY = Math.round(drawY - offsetY);

    console.log('标记绘制信息:', {
      pixelPos, drawX, drawY, finalX, finalY, 
      width, height, scaleX, scaleY,
      markerRect: markerRect ? {width: markerRect.width, height: markerRect.height} : null
    });

    // 绘制markerContent
    if (markerContent && markerContent.tagName && 
        (markerContent.tagName.toLowerCase() === 'img' || markerContent.tagName.toLowerCase() === 'canvas')) {
      ctx.drawImage(markerContent, finalX, finalY, width, height);
    } else {
      // 如果标记不是图片或画布，绘制一个简单的红色圆点
      ctx.save();
      ctx.beginPath();
      ctx.arc(finalX + offsetX, finalY + offsetY, Math.max(6, Math.floor(Math.min(width, height) / 6)), 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(255,0,0,0.9)';
      ctx.fill();
      ctx.restore();
    }
  } catch (e) {
    console.error('drawMarkerToCanvas: 绘制过程中发生错误', e);
  }
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
                    markerContent.style.zIndex = ''; 
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

//分析街景图
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
    
    // 关键修改：在截图前强制同步地图状态
    await new Promise(resolve => {
      const map = mapInstance.value;
      if (map && map.render && map.render instanceof Function) {
        // 强制地图重新渲染以确保状态同步
        map.render();
      }
      setTimeout(resolve, 300); // 等待地图状态稳定
    });
    
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
        
        // 关键修改：等待标记显示完成
        await new Promise(resolve => setTimeout(resolve, 100));
      } catch (e) {
        console.warn('确保标记可见失败:', e);
      }
      
      // 截取地图截图 - 增加重试机制
      let mapSnapshot = null;
      let retryCount = 0;
      while (!mapSnapshot && retryCount < 3) {
        mapSnapshot = await captureMapSnapshot(true, markerInfo.marker);
        if (!mapSnapshot) {
          retryCount++;
          await new Promise(resolve => setTimeout(resolve, 500));
        }
      }
      
      if (!mapSnapshot) {
        console.error(`第${i+1}个标记截图失败`);
        continue;
      }
      
      // 获取街景图数据和问题描述
      const streetImageUrl = markerInfo.imageUrl;
      const position = markerInfo.position;
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
      
      // 构建分析数据
      analyses.push({
        map_image_data: mapSnapshot,
        street_image_data: streetImageUrl,
        description: description, 
        position: position,
        // 关键修改：添加地图状态信息用于调试
        map_state: {
          center: mapInstance.value.getCenter(),
          zoom: mapInstance.value.getZoom(),
          pitch: mapInstance.value.getPitch(),
          rotation: mapInstance.value.getRotation()
        }
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
    
    // 发送批量分析请求
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
            text: `街景点分析报告（位置：${item.position.lng?.toFixed(6) || '未知'}, ${item.position.lat?.toFixed(6) || '未知'}）:\n${item.analysis}`
          });
        } else if (item.error) {
          messages.value.push({
            role: 'system',
            text: `第${item.index + 1}个点分析失败: ${item.error}`
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


// 恢复地图交互状态
function restoreMapInteractions() {
  // 确保退出选择模式
  if (selectMode.value) {
    exitSelectMode();
  }
  
  // 确保地图控件正常显示
  showMapControls();
  
  console.log('地图交互状态已恢复');
}

// 修改：重置地图状态函数，添加参数控制是否清除选区
function resetMapState(clearSelection = true) {
  console.log('开始重置地图状态...', { clearSelection });
  
  // 确保退出选择模式
  if (selectMode.value) {
    exitSelectMode();
  }
  
  // 根据参数决定是否清除选区
  if (clearSelection) {
    // 重置选择状态
    selectState.drawing = false;
    selectState.points = [];
    selectState.hasSelection = false;
    selectState.geoPoints = null;
    selectState.currentPath = null;
    console.log('已清除选区状态');
  } else {
    console.log('保持选区状态:', {
      hasSelection: selectState.hasSelection,
      geoPoints: selectState.geoPoints ? selectState.geoPoints.length : 0
    });
  }
  
  // 确保地图交互正常
  try {
    const map = mapInstance.value;
    if (map && typeof map.setStatus === 'function') {
      map.setStatus({ 
        dragEnable: true, 
        scrollWheel: true, 
        doubleClickZoom: true,
        rotateEnable: true,
        pitchEnable: true
      });
      console.log('地图交互状态已重置');
    }
  } catch (e) {
    console.error('重置地图状态失败:', e);
  }
  
  // 显示地图控件
  showMapControls();
  
  // 重绘覆盖层
  nextTick(() => {
    try {
      redraw();
    } catch (error) {
      console.error('重绘时发生错误:', error);
    }
  });
  
  console.log('地图状态重置完成');
}


function showMapControls() {
  setTimeout(() => {
    // 修改：显示整个图层控件容器
    const layerList = document.querySelector('.amap-ctrl-list-layer');
    if (layerList) {
      layerList.style.display = 'block';
    }
  }, 100);
}




//---------------------------------------------------------------------------------
//-----------------------------------地图截图设计-----------------------------------
//---------------------------------------------------------------------------------


// 裁剪图片工具函数
function cropRectangleImage(canvas, container, rect) {
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
  
  // 首先尝试查找高德地图的canvas
  const canvases = Array.from(container.querySelectorAll('canvas'));
  if (canvases.length === 0) return null;
  
  // 优先查找有WebGL上下文的canvas（通常是地图画布）
  for (const c of canvases) {
    try {
      const gl = c.getContext && (c.getContext('webgl') || c.getContext('webgl2') || c.getContext('experimental-webgl'));
      if (gl) return c;
    } catch (e) {}
  }
  
  // 如果没有WebGL上下文，选择最大的canvas
  canvases.sort((a, b) => (b.width * b.height) - (a.width * a.height));
  return canvases[0];
}



async function captureOverheadImages() {
  const map = mapInstance.value;
  
  return new Promise(async (resolve) => {
    // 保存当前地图样式
    let originalStyle = null;
    try {
      if (map.getStyle) {
        originalStyle = map.getStyle();
      }
    } catch (e) {
      console.log('无法获取当前地图样式，使用默认处理');
    }
    
    // 应用隐藏文字和路网的样式
    try {
      if (map.setStyle) {
        map.setStyle(hiddenMapStyle);
        console.log('已应用隐藏文字和路网的样式');
      }
    } catch (e) {
      console.error('设置地图样式失败:', e);
    }
    
    // 等待样式生效
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const container = (typeof map.getContainer === 'function'
      ? map.getContainer()
      : document.getElementById('fudan-map'));

    const canvas = findMapCanvas(container);
    if (!canvas) {
      console.error('未找到地图 canvas，无法导出截图');
      // 恢复原始样式
      if (originalStyle && map.setStyle) {
        map.setStyle(originalStyle);
      }
      resolve();
      return;
    }
    
    if (typeof canvas.toDataURL !== 'function') {
      console.error('浏览器不支持 canvas.toDataURL()');
      // 恢复原始样式
      if (originalStyle && map.setStyle) {
        map.setStyle(originalStyle);
      }
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
        // 恢复原始样式
        if (originalStyle && map.setStyle) {
          map.setStyle(originalStyle);
        }
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
        // 恢复原始样式
        if (originalStyle && map.setStyle) {
          map.setStyle(originalStyle);
        }
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
      // 恢复原始样式
      if (originalStyle && map.setStyle) {
        map.setStyle(originalStyle);
        console.log('已恢复原始地图样式');
      }
      resolve();
    }
  });
}

//切换图层工具，使用html元素
function switchToStandardLayer() {
  return new Promise((resolve, reject) => {
    try {
      // 修改：在切换图层时，先显示图层控件容器
      const layerList = document.querySelector('.amap-ctrl-list-layer');
      if (layerList) {
        layerList.style.display = 'block';
      }
      
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
      // 修改：在切换图层时，先显示图层控件容器
      const layerList = document.querySelector('.amap-ctrl-list-layer');
      if (layerList) {
        layerList.style.display = 'block';
      }
      
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
    const standardBaseImage = await cropRectangleImage(canvas, container, rect);
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
  
  // 发送消息后立即隐藏输入区域
  showChatInput.value = false;
  
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
  
  // 显示输入区域
  showChatInput.value = true;
  activeFunction.value = 'ai-analysis';
  
  // 等待用户输入风格建议的状态
  isWaitingForStyleSuggestion.value = true;
  
  // 先获取技术经济指标数据
  console.log("开始获取技术经济指标数据...");
  const indicatorsSuccess = await fetchEconomicIndicators();
  
  // 修复技术经济指标转换逻辑
  let economicIndicatorsStr = '';
  if (economicIndicators.value && Object.keys(economicIndicators.value).length > 0) {
    console.log("经济指标数据获取成功:", economicIndicators.value);
    
    // 过滤掉不需要的字段
    const excludeKeys = ['id', 'created_at'];
    const filteredIndicators = {};
    
    Object.entries(economicIndicators.value).forEach(([key, value]) => {
      if (!excludeKeys.includes(key) && value !== null && value !== undefined) {
        filteredIndicators[key] = value;
      }
    });
    
    // 转换为易读的字符串格式
    economicIndicatorsStr = Object.entries(filteredIndicators)
      .map(([key, value]) => {
        const formattedKey = key.split('_')
          .map(word => word.charAt(0).toUpperCase() + word.slice(1))
          .join(' ');
        return `${formattedKey}: ${value}`;
      })
      .join('\n');
    
    console.log("处理后的经济指标字符串:", economicIndicatorsStr);
  } else {
    console.log("经济指标数据为空或获取失败");
    economicIndicatorsStr = '暂无技术经济指标数据';
  }
  
  let promptText = '请输入您对本次规划的风格建议，然后点击发送。';
  
  
  messages.value.push({ 
    role: 'system', 
    text: promptText 
  });
  
  // 自动聚焦到输入框
  nextTick(() => {
    const textarea = document.querySelector('.chat-input textarea');
    if (textarea) {
      textarea.focus();
    }
  });
  
  scrollToBottom();
}

async function handleStyleSuggestion(styleSuggestion) {
  try {
    // 隐藏输入区域
    showChatInput.value = false;
    activeFunction.value = '';
    
    messages.value.push({ role: 'user', text: `风格建议：${styleSuggestion}` });
    newMessage.value = '';
    isWaitingForStyleSuggestion.value = false;
    
    // 确保技术经济指标数据是最新的
    console.log("再次确认技术经济指标数据...");
    await fetchEconomicIndicators();
    
    // 重新构建经济指标字符串（确保使用最新数据）
    let economicIndicatorsStr = '';
    if (economicIndicators.value && Object.keys(economicIndicators.value).length > 0) {
      const excludeKeys = ['id', 'created_at'];
      const filteredIndicators = {};
      
      Object.entries(economicIndicators.value).forEach(([key, value]) => {
        if (!excludeKeys.includes(key) && value !== null && value !== undefined) {
          filteredIndicators[key] = value;
        }
      });
      
      economicIndicatorsStr = Object.entries(filteredIndicators)
        .map(([key, value]) => {
          const formattedKey = key.split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
          return `${formattedKey}: ${value}`;
        })
        .join('\n');
    } else {
      economicIndicatorsStr = '暂无技术经济指标数据';
    }
    
    // 准备街景图分析结果，确保数据结构正确
    const streetViewAnalyses = (streetViewAnalysisResults.value || []).map((item, index) => {
      return {
        index: index,
        analysis: item.analysis || '',
        error: item.error || null,
        position: item.position || { lng: 0, lat: 0 },
        description: item.description || '用户未提供具体问题描述'
      };
    });
    
    // 调试信息
    console.log("=== 发送到后端的数据 ===");
    console.log("风格建议:", styleSuggestion);
    console.log("调研总结:", surveySummary.value);
    console.log("经济指标字符串:", economicIndicatorsStr);
    console.log("街景图分析结果数量:", streetViewAnalyses.length);
    console.log("街景图分析详情:", streetViewAnalyses);
    console.log("===================");
    
    // 发送分析请求
    const response = await fetch('http://127.0.0.1:5000/analyze-with-ai', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        style_suggestion: styleSuggestion,  
        survey_summary: surveySummary.value,
        economic_indicators_str: economicIndicatorsStr,
        street_view_analyses: streetViewAnalyses
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
  } catch (error) {
    messages.value.push({ 
      role: 'system', 
      text: 'AI分析时发生错误: ' + error.message 
    });
  } finally {
    scrollToBottom();
  }
}


//---------------------------------------------------------------------------------
//-----------------------------------三维草图生成设计-------------------------------
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
    
    // 使用总结后的prompt调用草图生成接口
    messages.value.push({ 
      role: 'system', 
      text: `正在生成多视角规划图${usePro ? '（增强版）' : ''}，请稍候...` 
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
      !msg.text.includes('正在生成多视角规划图，请稍后……')
    );
    
    if (result.ok && result.images && result.images.length >= 3) {
      // 将生成的三张图片分别存储到对应的集合
      const [birdView, flatView, topView] = result.images;
      
      // 鸟瞰图
      imageCollections.value.bird_view.images.push(birdView);
      imageCollections.value.bird_view.currentIndex = imageCollections.value.bird_view.images.length - 1;
      
      // 平视图  
      imageCollections.value.flat_view.images.push(flatView);
      imageCollections.value.flat_view.currentIndex = imageCollections.value.flat_view.images.length - 1;
      
      // 顶视图
      imageCollections.value.top_view.images.push(topView);
      imageCollections.value.top_view.currentIndex = imageCollections.value.top_view.images.length - 1;
      
      // 初始化历史记录
      [imageCollections.value.bird_view, imageCollections.value.flat_view, imageCollections.value.top_view].forEach(collection => {
        if (!collection.history[collection.currentIndex]) {
          collection.history[collection.currentIndex] = [];
        }
        collection.history[collection.currentIndex].push(collection.images[collection.currentIndex]);
        collection.currentHistoryIndex[collection.currentIndex] = 0;
      });
      
      // 设置当前显示为鸟瞰图
      currentCollectionType.value = 'bird_view';
      currentPage.value = 'image-collection';
      hasGeneratedImage.value = true;
      
      messages.value.push({ 
        role: 'system', 
        text: `多视角规划图${usePro ? '（增强版）' : ''}生成成功！已生成鸟瞰图、平视图、顶视图。` 
      });      
    } else {
      messages.value.push({ 
        role: 'system', 
        text: `多视角图生成失败: ` + (result.error || '未知错误') 
      });
    }
  } catch (error) {
    messages.value.push({ 
      role: 'system', 
      text: `生成多视角图时发生错误: ` + error.message 
    });
  } finally {
    scrollToBottom();
  }
}

function onImageLoad() {
  console.log('图片加载成功');
}

function getCollectionTitle() {
  const titles = {
    'bird_view': '鸟瞰图',
    'flat_view': '平视图', 
    'top_view': '顶视图',
    'zoning': '功能分区图',
    'stream_map': '流线分析图',
    'effect_view': '效果图' 
  };
  return titles[currentCollectionType.value] || '图片集';
}

// 显示图片集函数
function showImageCollection() {
  const hasImages = imageCollections.value.bird_view.images.length > 0 || 
                   imageCollections.value.flat_view.images.length > 0 || 
                   imageCollections.value.top_view.images.length > 0 ||
                   imageCollections.value.zoning.images.length > 0 ||
                   imageCollections.value.effect_view.images.length > 0 ||
                   imageCollections.value.stream_map.images.length > 0; 
  
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
//-----------------------------------流线分析图设计---------------------------------
//---------------------------------------------------------------------------------

// 生成流线分析图
async function generateStreamMap() {
  try {
    messages.value.push({
      role: 'system',
      text: '正在生成流线分析图，请稍候...'
    });
    scrollToBottom();
    
    const response = await fetch('http://127.0.0.1:5000/generate-stream-map', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({})
    });
    
    const result = await response.json();
    messages.value = messages.value.filter(msg => 
      !msg.text.includes('正在生成流线分析图，请稍候...')
    );
    
    if (result.ok && result.images && result.images.length > 0) {
      // 将生成的流线图添加到流线图集
      imageCollections.value.stream_map.images.push(result.images[0]);
      imageCollections.value.stream_map.currentIndex = imageCollections.value.stream_map.images.length - 1;
      
      // 初始化历史记录
      if (!imageCollections.value.stream_map.history[imageCollections.value.stream_map.currentIndex]) {
        imageCollections.value.stream_map.history[imageCollections.value.stream_map.currentIndex] = [];
      }
      imageCollections.value.stream_map.history[imageCollections.value.stream_map.currentIndex].push(result.images[0]);
      imageCollections.value.stream_map.currentHistoryIndex[imageCollections.value.stream_map.currentIndex] = 0;
      
      // 设置当前显示的流线图集
      currentCollectionType.value = 'stream_map';
      currentPage.value = 'image-collection';
      hasGeneratedImage.value = true;
      
      // 根据使用的参考图类型显示不同的成功消息
      const referenceType = result.reference_image_type;
      let successMessage = '✅ 流线分析图生成成功！';
      messages.value.push({
        role: 'system',
        text: successMessage
      });
      
    } else {
      messages.value.push({
        role: 'system',
        text: '流线分析图生成失败: ' + (result.error || '未知错误')
      });
    }
    
  } catch (error) {
    messages.value.push({
      role: 'system',
      text: '生成流线分析图时发生错误: ' + error.message
    });
  } finally {
    scrollToBottom();
  }
}



//---------------------------------------------------------------------------------
//-----------------------------------实景效果图部分---------------------------------
//---------------------------------------------------------------------------------
async function generateEffectView() {
  showToolbar.value = false;
  
  // 检查是否有AI分析结果
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
      text: '请先进行AI分析再生成效果图'
    });
    scrollToBottom();
    return;
  }
  
  try {
    messages.value.push({
      role: 'system',
      text: '正在生成效果图提示词，请稍候...'
    });
    scrollToBottom();
    
    // 调用现有的summarize-prompt路由生成总结内容
    const summarizeResponse = await fetch('http://127.0.0.1:5000/summarize-prompt', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        analysis: latestAnalysis
      })
    });
    
    const summarizeResult = await summarizeResponse.json();
    messages.value = messages.value.filter(msg => 
      !msg.text.includes('正在生成效果图提示词，请稍候...')
    );
    
    if (!summarizeResult.ok || !summarizeResult.summarized_prompt) {
      messages.value.push({
        role: 'system',
        text: '效果图提示词生成失败: ' + (summarizeResult.error || '未知错误')
      });
      scrollToBottom();
      return;
    }
    
    // 提取总结的prompt内容
    let summarizedContent = summarizeResult.summarized_prompt;
    const promptMatch = summarizedContent.match(/总结的prompt为：(.+)/);
    if (promptMatch && promptMatch[1]) {
      summarizedContent = promptMatch[1].trim();
    }
    
    messages.value.push({
      role: 'system',
      text: '效果图提示词生成成功，正在生成效果图...'
    });
    scrollToBottom();
    
    // 将总结的内容传递给generate-effect-image路由
    const imageResponse = await fetch('http://127.0.0.1:5000/generate-effect-image', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        summarized_prompt: summarizedContent
      })
    });
    
    const imageResult = await imageResponse.json();
    messages.value = messages.value.filter(msg => 
      !msg.text.includes('效果图提示词生成成功，正在生成效果图...')
    );
    
    if (imageResult.ok && imageResult.images && imageResult.images.length > 0) {
      // 初始化效果图集合
      imageCollections.value.effect_view = imageCollections.value.effect_view || {
        images: [],
        currentIndex: 0,
        history: [],
        currentHistoryIndex: []
      };
      
      // 将生成的效果图添加到效果图集
      imageCollections.value.effect_view.images.push(imageResult.images[0]);
      imageCollections.value.effect_view.currentIndex = imageCollections.value.effect_view.images.length - 1;
      
      // 初始化历史记录
      if (!imageCollections.value.effect_view.history[imageCollections.value.effect_view.currentIndex]) {
        imageCollections.value.effect_view.history[imageCollections.value.effect_view.currentIndex] = [];
      }
      imageCollections.value.effect_view.history[imageCollections.value.effect_view.currentIndex].push(imageResult.images[0]);
      imageCollections.value.effect_view.currentHistoryIndex[imageCollections.value.effect_view.currentIndex] = 0;
      
      // 设置当前显示的效果图集
      currentCollectionType.value = 'effect_view';
      currentPage.value = 'image-collection';
      hasGeneratedImage.value = true;
      
      messages.value.push({
        role: 'system',
        text: '✅ 效果图生成成功！'
      });
      
    } else {
      messages.value.push({
        role: 'system',
        text: '效果图生成失败: ' + (imageResult.error || '未知错误')
      });
    }
    
  } catch (error) {
    messages.value.push({
      role: 'system',
      text: '生成效果图时发生错误: ' + error.message
    });
  } finally {
    scrollToBottom();
  }
}





//---------------------------------------------------------------------------------
//-----------------------------------草图修改设计-----------------------------------
//---------------------------------------------------------------------------------

//草图修改建议工具函数
function suggestEdits() {
  if (imageCollections.value.bird_view.images.length === 0 && 
      imageCollections.value.flat_view.images.length === 0 && 
      imageCollections.value.top_view.images.length === 0) {
    alert('请先生成草图才能使用修改建议功能！');
    return;
  }
  
  // 显示输入区域
  showChatInput.value = true;
  activeFunction.value = 'suggest-edits';
  isWaitingForStyleSuggestion.value = false;
  isEditingSuggestion.value = true;
  
  messages.value.push({ 
    role: 'system', 
    text: '请输入您对当前草图的修改意见，然后点击发送。' 
  });
  
  // 自动聚焦到输入框
  nextTick(() => {
    const textarea = document.querySelector('.chat-input textarea');
    if (textarea) {
      textarea.focus();
    }
  });
  
  scrollToBottom();
}

async function handleSuggestionRequest(suggestionText) {
  if (!currentGeneratedImage.value) {
    alert('当前没有可修改的草图');
    return;
  }
  
  try {
    // 隐藏输入区域
    showChatInput.value = false;
    activeFunction.value = '';
    isEditingSuggestion.value = false;
    
    messages.value.push({ role: 'user', text: `修改建议：${suggestionText}` });
    newMessage.value = '';
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
//-----------------------------------图片展示部分-----------------------------------
//---------------------------------------------------------------------------------


// 进入图片集函数
function enterCollection(collectionType) {
  if (imageCollections.value[collectionType].images.length === 0) {
    messages.value.push({
      role: 'system',
      text: getCollectionUnavailableText(collectionType)
    });
    return;
  }
  
  currentCollectionType.value = collectionType;
  currentPage.value = 'image';
  hasGeneratedImage.value = true;
  restoreMapInteractionsOnly();
  console.log('进入图片浏览页面，选区状态保持');
}


// 获取图片集不可用时的提示文本
function getCollectionUnavailableText(collectionType) {
  const texts = {
    'bird_view': '暂无鸟瞰图，请先生成图片',
    'flat_view': '暂无平视图，请先生成图片',
    'top_view': '暂无顶视图，请先生成图片',
    'zoning': '暂无功能分区图，请先生成图片',
    'stream_map': '暂无流线分析图，请先生成图片',
    'effect_view': '暂无效果图，请先生成图片'
  };
  return texts[collectionType] || '暂无图片，请先生成图片';
}

// 返回图片集函数
function backToCollection() {
  currentPage.value = 'image-collection';
  hasGeneratedImage.value = true;
  console.log('返回图片集，保持选区状态');
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

//页面切换控制器
function togglePage() {
  if (currentPage.value === 'image') {
    currentPage.value = 'image-collection';
  } else if (currentPage.value === 'image-collection') {
    currentPage.value = 'map';
    hasGeneratedImage.value = 
      imageCollections.value.bird_view.images.length > 0 || 
      imageCollections.value.flat_view.images.length > 0 || 
      imageCollections.value.top_view.images.length > 0 ||
      imageCollections.value.zoning.images.length > 0 ||
      imageCollections.value.stream_map.images.length > 0 ||
      imageCollections.value.effect_view.images.length > 0;
    
    nextTick(() => {
      // 修复：在恢复交互前清理可能无效的选区状态
      cleanupInvalidSelection();
      restoreMapInteractionsOnly();
      
      if (overlayCanvas.value) {
        overlayCanvas.value.style.pointerEvents = selectMode.value ? 'auto' : 'none';
      }
      
      // 延迟重绘，确保地图完全加载
      setTimeout(() => {
        redraw();
      }, 100);
    });
    
  } else {
    const hasImages = 
      imageCollections.value.bird_view.images.length > 0 || 
      imageCollections.value.flat_view.images.length > 0 || 
      imageCollections.value.top_view.images.length > 0 ||
      imageCollections.value.zoning.images.length > 0 ||
      imageCollections.value.stream_map.images.length > 0 ||
      imageCollections.value.effect_view.images.length > 0;
    
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

// 清理可能包含无效坐标的选区状态
function cleanupInvalidSelection() {
  if (selectState.geoPoints && Array.isArray(selectState.geoPoints)) {
    const validGeoPoints = selectState.geoPoints.filter(point => 
      point && 
      typeof point.lng === 'number' && 
      typeof point.lat === 'number' &&
      !isNaN(point.lng) && 
      !isNaN(point.lat) &&
      isFinite(point.lng) && 
      isFinite(point.lat) &&
      point.lng >= -180 && point.lng <= 180 &&
      point.lat >= -90 && point.lat <= 90
    );
    
    if (validGeoPoints.length !== selectState.geoPoints.length) {
      console.warn(`清理了 ${selectState.geoPoints.length - validGeoPoints.length} 个无效坐标点`);
      selectState.geoPoints = validGeoPoints.length >= 3 ? validGeoPoints : null;
      selectState.hasSelection = selectState.geoPoints !== null;
    }
  }
  
  // 清理屏幕坐标点
  if (selectState.points && Array.isArray(selectState.points)) {
    selectState.points = selectState.points.filter(point => 
      point && 
      typeof point.x === 'number' && 
      typeof point.y === 'number' &&
      !isNaN(point.x) && 
      !isNaN(point.y) &&
      isFinite(point.x) && 
      isFinite(point.y)
    );
  }
}

//恢复地图交互，不清除选区
function restoreMapInteractionsOnly() {
  console.log('恢复地图交互状态（保留选区）...');
  
  // 确保退出选择模式
  if (selectMode.value) {
    selectMode.value = false;
  }
  
  // 恢复地图交互状态
  try {
    const map = mapInstance.value;
    if (map && typeof map.setStatus === 'function') {
      map.setStatus({ 
        dragEnable: true, 
        scrollWheel: true, 
        doubleClickZoom: true,
        rotateEnable: true,
        pitchEnable: true
      });
      console.log('地图交互状态已恢复');
    }
  } catch (e) {
    console.error('恢复地图交互失败:', e);
  }
  showMapControls();
  console.log('选区状态保持:', {
    hasSelection: selectState.hasSelection,
    geoPoints: selectState.geoPoints ? selectState.geoPoints.length : 0
  });
}

</script>










<style scoped>

@import './style.css';

</style>
