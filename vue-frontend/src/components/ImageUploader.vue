<template>
  <div class="image-uploader">
    <div class="upload-header">
      <h3>📸 Bilder hochladen</h3>
      <div class="upload-stats">
        <span class="file-count">{{ uploadedImages.length }} Datei(en)</span>
        <span class="total-size">{{ formatFileSize(totalSize) }}</span>
      </div>
    </div>

    <!-- Drag & Drop Zone -->
    <div 
      class="drop-zone"
      :class="{ 
        'drag-over': isDragOver, 
        'has-files': uploadedImages.length > 0 
      }"
      @drop="handleDrop"
      @dragover="handleDragOver"
      @dragenter="handleDragEnter"
      @dragleave="handleDragLeave"
      @click="triggerFileInput"
    >
      <div class="drop-zone-content">
        <div class="upload-icon">📁</div>
        <div class="upload-text">
          <p class="primary-text">
            Bilder hier hineinziehen oder klicken zum Auswählen
          </p>
          <p class="secondary-text">
            Unterstützt: JPG, PNG, GIF, WebP (max. {{ maxFileSize }}MB pro Datei)
          </p>
        </div>
      </div>
      
      <!-- Hidden file input -->
      <input
        ref="fileInput"
        type="file"
        multiple
        accept="image/*"
        @change="handleFileSelect"
        style="display: none"
      />
    </div>

    <!-- Image Thumbnails Grid -->
    <div v-if="uploadedImages.length > 0" class="thumbnails-grid">
      <div 
        v-for="(image, index) in uploadedImages" 
        :key="image.id"
        class="thumbnail-item"
        :class="{ 'uploading': image.uploading, 'error': image.error }"
      >
        <!-- Thumbnail Image -->
        <div class="thumbnail-wrapper">
          <img 
            :src="image.thumbnail" 
            :alt="image.name"
            class="thumbnail-image"
            @click="openImagePreview(image)"
          />
          
          <!-- Upload Progress -->
          <div v-if="image.uploading" class="upload-progress">
            <div class="progress-bar">
              <div 
                class="progress-fill" 
                :style="{ width: image.progress + '%' }"
              ></div>
            </div>
            <span class="progress-text">{{ image.progress }}%</span>
          </div>
          
          <!-- Error Overlay -->
          <div v-if="image.error" class="error-overlay">
            <span class="error-icon">⚠️</span>
            <span class="error-text">{{ image.error }}</span>
          </div>
          
          <!-- Remove Button -->
          <button 
            class="remove-btn"
            @click.stop="removeImage(index)"
            :disabled="image.uploading"
          >
            ✕
          </button>
        </div>
        
        <!-- Image Info -->
        <div class="image-info">
          <div class="image-name" :title="image.name">{{ image.name }}</div>
          <div class="image-size">{{ formatFileSize(image.size) }}</div>
          <div v-if="image.uploadedAt" class="upload-date">
            {{ formatDate(image.uploadedAt) }}
          </div>
        </div>
      </div>
    </div>

    <!-- Upload Actions -->
    <div v-if="uploadedImages.length > 0" class="upload-actions">
      <button 
        class="action-btn upload-all-btn"
        @click="uploadAllImages"
        :disabled="isUploading || allImagesUploaded"
      >
        <span v-if="isUploading">🔄 Uploading...</span>
        <span v-else-if="allImagesUploaded">✅ Alle hochgeladen</span>
        <span v-else>📤 Alle hochladen ({{ pendingUploads }})</span>
      </button>
      
      <button 
        class="action-btn clear-all-btn"
        @click="clearAllImages"
        :disabled="isUploading"
      >
        🗑️ Alle entfernen
      </button>
    </div>

    <!-- Image Preview Modal -->
    <div v-if="previewImage" class="preview-modal" @click="closePreview">
      <div class="preview-content" @click.stop>
        <button class="preview-close" @click="closePreview">✕</button>
        <img :src="previewImage.url || previewImage.thumbnail" :alt="previewImage.name" />
        <div class="preview-info">
          <h4>{{ previewImage.name }}</h4>
          <p>Größe: {{ formatFileSize(previewImage.size) }}</p>
          <p v-if="previewImage.uploadedAt">
            Hochgeladen: {{ formatDate(previewImage.uploadedAt) }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ImageUploader',
  props: {
    maxFileSize: {
      type: Number,
      default: 10 // MB
    },
    maxFiles: {
      type: Number,
      default: 20
    },
    uploadEndpoint: {
      type: String,
      default: '/api/upload/images'
    },
    persistenceKey: {
      type: String,
      default: 'uploaded-images'
    }
  },
  data() {
    return {
      uploadedImages: [],
      isDragOver: false,
      isUploading: false,
      previewImage: null,
      nextImageId: 1
    }
  },
  computed: {
    totalSize() {
      return this.uploadedImages.reduce((total, img) => total + img.size, 0);
    },
    pendingUploads() {
      return this.uploadedImages.filter(img => !img.uploaded && !img.uploading && !img.error).length;
    },
    allImagesUploaded() {
      return this.uploadedImages.length > 0 && this.uploadedImages.every(img => img.uploaded);
    }
  },
  mounted() {
    this.loadPersistedImages();
    
    // Prevent default drag behaviors on the document
    document.addEventListener('dragover', this.preventDefaults);
    document.addEventListener('drop', this.preventDefaults);
  },
  beforeUnmount() {
    document.removeEventListener('dragover', this.preventDefaults);
    document.removeEventListener('drop', this.preventDefaults);
  },
  methods: {
    preventDefaults(e) {
      e.preventDefault();
      e.stopPropagation();
    },
    
    handleDragEnter(e) {
      this.preventDefaults(e);
      this.isDragOver = true;
    },
    
    handleDragOver(e) {
      this.preventDefaults(e);
      this.isDragOver = true;
    },
    
    handleDragLeave(e) {
      this.preventDefaults(e);
      // Only set to false if we're leaving the drop zone entirely
      if (!this.$el.contains(e.relatedTarget)) {
        this.isDragOver = false;
      }
    },
    
    handleDrop(e) {
      this.preventDefaults(e);
      this.isDragOver = false;
      
      const files = Array.from(e.dataTransfer.files);
      this.processFiles(files);
    },
    
    triggerFileInput() {
      this.$refs.fileInput.click();
    },
    
    handleFileSelect(e) {
      const files = Array.from(e.target.files);
      this.processFiles(files);
      // Clear the input so the same file can be selected again
      e.target.value = '';
    },
    
    processFiles(files) {
      const imageFiles = files.filter(file => file.type.startsWith('image/'));
      
      if (imageFiles.length === 0) {
        this.showNotification('Keine gültigen Bilddateien gefunden', 'warning');
        return;
      }
      
      // Check file count limit
      if (this.uploadedImages.length + imageFiles.length > this.maxFiles) {
        this.showNotification(`Maximal ${this.maxFiles} Dateien erlaubt`, 'error');
        return;
      }
      
      imageFiles.forEach(file => {
        // Check file size
        if (file.size > this.maxFileSize * 1024 * 1024) {
          this.showNotification(`${file.name} ist zu groß (max. ${this.maxFileSize}MB)`, 'error');
          return;
        }
        
        this.addImageFile(file);
      });
    },
    
    addImageFile(file) {
      const imageData = {
        id: this.nextImageId++,
        name: file.name,
        size: file.size,
        file: file,
        thumbnail: null,
        url: null,
        uploading: false,
        uploaded: false,
        progress: 0,
        error: null,
        addedAt: new Date().toISOString()
      };
      
      // Generate thumbnail
      this.generateThumbnail(file).then(thumbnail => {
        imageData.thumbnail = thumbnail;
        this.$forceUpdate(); // Force reactivity update
      });
      
      this.uploadedImages.push(imageData);
      this.persistImages();
      
      this.showNotification(`${file.name} hinzugefügt`, 'success');
    },
    
    generateThumbnail(file) {
      return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = (e) => {
          const img = new Image();
          img.onload = () => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            
            // Calculate thumbnail size (max 200x200, maintain aspect ratio)
            const maxSize = 200;
            let { width, height } = img;
            
            if (width > height) {
              if (width > maxSize) {
                height = (height * maxSize) / width;
                width = maxSize;
              }
            } else {
              if (height > maxSize) {
                width = (width * maxSize) / height;
                height = maxSize;
              }
            }
            
            canvas.width = width;
            canvas.height = height;
            
            ctx.drawImage(img, 0, 0, width, height);
            resolve(canvas.toDataURL('image/jpeg', 0.8));
          };
          img.src = e.target.result;
        };
        reader.readAsDataURL(file);
      });
    },
    
    removeImage(index) {
      const image = this.uploadedImages[index];
      this.uploadedImages.splice(index, 1);
      this.persistImages();
      
      this.showNotification(`${image.name} entfernt`, 'info');
      
      // Emit event for parent component
      this.$emit('image-removed', image);
    },
    
    clearAllImages() {
      if (confirm('Alle Bilder entfernen?')) {
        this.uploadedImages = [];
        this.persistImages();
        this.showNotification('Alle Bilder entfernt', 'info');
        
        this.$emit('all-images-cleared');
      }
    },
    
    async uploadAllImages() {
      const imagesToUpload = this.uploadedImages.filter(img => !img.uploaded && !img.uploading && !img.error);
      
      if (imagesToUpload.length === 0) {
        return;
      }
      
      this.isUploading = true;
      
      for (const image of imagesToUpload) {
        await this.uploadSingleImage(image);
      }
      
      this.isUploading = false;
      this.persistImages();
      
      this.showNotification('Upload abgeschlossen', 'success');
      this.$emit('upload-completed', this.uploadedImages.filter(img => img.uploaded));
    },
    
    async uploadSingleImage(image) {
      image.uploading = true;
      image.progress = 0;
      image.error = null;
      
      try {
        const formData = new FormData();
        formData.append('image', image.file);
        formData.append('name', image.name);
        
        const response = await fetch(this.uploadEndpoint, {
          method: 'POST',
          body: formData,
          onUploadProgress: (progressEvent) => {
            image.progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          }
        });
        
        if (!response.ok) {
          throw new Error(`Upload failed: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        image.uploaded = true;
        image.uploading = false;
        image.progress = 100;
        image.url = result.url;
        image.uploadedAt = new Date().toISOString();
        
        this.$emit('image-uploaded', image, result);
        
      } catch (error) {
        image.uploading = false;
        image.error = error.message;
        console.error('Upload error:', error);
      }
    },
    
    openImagePreview(image) {
      this.previewImage = image;
    },
    
    closePreview() {
      this.previewImage = null;
    },
    
    persistImages() {
      try {
        // Only persist metadata, not the actual file objects
        const persistData = this.uploadedImages.map(img => ({
          id: img.id,
          name: img.name,
          size: img.size,
          thumbnail: img.thumbnail,
          url: img.url,
          uploaded: img.uploaded,
          uploadedAt: img.uploadedAt,
          addedAt: img.addedAt
        }));
        
        localStorage.setItem(this.persistenceKey, JSON.stringify(persistData));
      } catch (error) {
        console.warn('Failed to persist images:', error);
      }
    },
    
    loadPersistedImages() {
      try {
        const persistedData = localStorage.getItem(this.persistenceKey);
        if (persistedData) {
          const images = JSON.parse(persistedData);
          this.uploadedImages = images.map(img => ({
            ...img,
            file: null, // File objects can't be persisted
            uploading: false,
            progress: 0,
            error: null
          }));
          
          // Update next ID
          if (images.length > 0) {
            this.nextImageId = Math.max(...images.map(img => img.id)) + 1;
          }
        }
      } catch (error) {
        console.warn('Failed to load persisted images:', error);
      }
    },
    
    formatFileSize(bytes) {
      if (bytes === 0) return '0 Bytes';
      
      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    formatDate(dateString) {
      const date = new Date(dateString);
      return date.toLocaleDateString('de-DE') + ' ' + date.toLocaleTimeString('de-DE', { 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    },
    
    showNotification(message, type = 'info') {
      // Emit notification event for parent component to handle
      this.$emit('notification', { message, type });
      
      // Fallback console log
      console.log(`[ImageUploader] ${type.toUpperCase()}: ${message}`);
    }
  }
}
</script>

<style scoped>
.image-uploader {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.upload-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 2px solid #e0e0e0;
}

.upload-header h3 {
  margin: 0;
  color: #333;
  font-size: 1.5em;
}

.upload-stats {
  display: flex;
  gap: 15px;
  font-size: 0.9em;
  color: #666;
}

.file-count {
  font-weight: 600;
}

.drop-zone {
  border: 3px dashed #ccc;
  border-radius: 12px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #fafafa;
  margin-bottom: 20px;
}

.drop-zone:hover {
  border-color: #2196F3;
  background: #f0f8ff;
}

.drop-zone.drag-over {
  border-color: #4CAF50;
  background: #f0fff0;
  transform: scale(1.02);
}

.drop-zone.has-files {
  border-style: solid;
  border-color: #4CAF50;
  background: #f8fff8;
}

.drop-zone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
}

.upload-icon {
  font-size: 3em;
  opacity: 0.6;
}

.upload-text .primary-text {
  font-size: 1.1em;
  font-weight: 600;
  color: #333;
  margin: 0 0 5px 0;
}

.upload-text .secondary-text {
  font-size: 0.9em;
  color: #666;
  margin: 0;
}

.thumbnails-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.thumbnail-item {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  overflow: hidden;
  transition: transform 0.2s ease;
}

.thumbnail-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.thumbnail-item.uploading {
  opacity: 0.8;
}

.thumbnail-item.error {
  border: 2px solid #f44336;
}

.thumbnail-wrapper {
  position: relative;
  aspect-ratio: 1;
  overflow: hidden;
}

.thumbnail-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  cursor: pointer;
  transition: transform 0.2s ease;
}

.thumbnail-image:hover {
  transform: scale(1.05);
}

.upload-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0,0,0,0.8);
  color: white;
  padding: 8px;
  text-align: center;
}

.progress-bar {
  width: 100%;
  height: 4px;
  background: rgba(255,255,255,0.3);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 4px;
}

.progress-fill {
  height: 100%;
  background: #4CAF50;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.8em;
  font-weight: 600;
}

.error-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(244, 67, 54, 0.9);
  color: white;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 10px;
}

.error-icon {
  font-size: 2em;
  margin-bottom: 5px;
}

.error-text {
  font-size: 0.8em;
  font-weight: 600;
}

.remove-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 50%;
  background: rgba(244, 67, 54, 0.9);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
  transition: all 0.2s ease;
}

.remove-btn:hover {
  background: #f44336;
  transform: scale(1.1);
}

.remove-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.image-info {
  padding: 12px;
}

.image-name {
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.image-size {
  font-size: 0.8em;
  color: #666;
  margin-bottom: 2px;
}

.upload-date {
  font-size: 0.7em;
  color: #999;
}

.upload-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-top: 20px;
}

.action-btn {
  padding: 12px 24px;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.9em;
}

.upload-all-btn {
  background: #4CAF50;
  color: white;
}

.upload-all-btn:hover:not(:disabled) {
  background: #45a049;
}

.upload-all-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.clear-all-btn {
  background: #f44336;
  color: white;
}

.clear-all-btn:hover:not(:disabled) {
  background: #da190b;
}

.clear-all-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.preview-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  cursor: pointer;
}

.preview-content {
  max-width: 90vw;
  max-height: 90vh;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  cursor: default;
  position: relative;
}

.preview-close {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 50%;
  background: rgba(0,0,0,0.7);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  z-index: 1001;
}

.preview-content img {
  max-width: 100%;
  max-height: 70vh;
  display: block;
}

.preview-info {
  padding: 20px;
  background: white;
}

.preview-info h4 {
  margin: 0 0 10px 0;
  color: #333;
}

.preview-info p {
  margin: 5px 0;
  color: #666;
  font-size: 0.9em;
}

/* Dark theme support */
@media (prefers-color-scheme: dark) {
  .image-uploader {
    color: #e0e0e0;
  }
  
  .upload-header h3 {
    color: #e0e0e0;
  }
  
  .drop-zone {
    background: #2a2a2a;
    border-color: #555;
  }
  
  .drop-zone:hover {
    background: #333;
  }
  
  .thumbnail-item {
    background: #2a2a2a;
  }
  
  .image-info {
    background: #2a2a2a;
  }
  
  .image-name {
    color: #e0e0e0;
  }
  
  .preview-content {
    background: #2a2a2a;
  }
  
  .preview-info {
    background: #2a2a2a;
  }
  
  .preview-info h4 {
    color: #e0e0e0;
  }
}

/* Responsive design */
@media (max-width: 768px) {
  .thumbnails-grid {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 15px;
  }
  
  .upload-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .upload-stats {
    flex-direction: column;
    gap: 5px;
  }
  
  .upload-actions {
    flex-direction: column;
  }
  
  .action-btn {
    width: 100%;
  }
}
</style> 