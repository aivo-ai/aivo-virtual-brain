const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8080'

// Coursework Types
export interface CourseworkAsset {
  id: string
  learnerId?: string
  title: string
  description?: string
  type: 'pdf' | 'image' | 'video' | 'audio' | 'document'
  fileName: string
  fileSize: number
  mimeType: string
  url: string
  uploadedAt: string
  subject?: string
  topic?: string
  gradeBand?: string
  tags: string[]
  ocrContent?: string
  extractedTopics?: string[]
  metadata?: {
    pageCount?: number
    duration?: number
    dimensions?: { width: number; height: number }
    extractedText?: string
  }
}

export interface CourseworkUploadRequest {
  learnerId?: string
  title: string
  description?: string
  subject?: string
  topic?: string
  gradeBand?: string
  tags?: string[]
}

export interface CourseworkUploadResponse {
  asset: CourseworkAsset
  uploadUrl: string
}

export interface CourseworkListRequest {
  learnerId?: string
  subject?: string
  topic?: string
  type?: string
  gradeBand?: string
  search?: string
  limit?: number
  offset?: number
}

export interface CourseworkListResponse {
  assets: CourseworkAsset[]
  total: number
  hasMore: boolean
}

export interface OCRPreviewResponse {
  extractedText: string
  extractedTopics: string[]
  confidence: number
  suggestedTags: string[]
}

class CourseworkClient {
  private getAuthHeaders() {
    const token = localStorage.getItem('token')
    return {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    }
  }

  async listAssets(
    params: CourseworkListRequest
  ): Promise<CourseworkListResponse> {
    const queryParams = new URLSearchParams()

    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        queryParams.append(key, String(value))
      }
    })

    const response = await fetch(
      `${API_BASE}/coursework-ingest-svc/assets?${queryParams}`,
      {
        method: 'GET',
        headers: this.getAuthHeaders(),
      }
    )

    if (!response.ok) {
      throw new Error(
        `Failed to fetch coursework assets: ${response.statusText}`
      )
    }

    return response.json()
  }

  // Alias for getAssets to match Index page usage
  async getAssets(filters: any): Promise<any> {
    return this.listAssets(filters)
  }

  async getAsset(assetId: string): Promise<CourseworkAsset> {
    const response = await fetch(
      `${API_BASE}/coursework-ingest-svc/assets/${assetId}`,
      {
        method: 'GET',
        headers: this.getAuthHeaders(),
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to fetch asset: ${response.statusText}`)
    }

    return response.json()
  }

  async createAsset(
    assetData: CourseworkUploadRequest
  ): Promise<CourseworkUploadResponse> {
    const response = await fetch(`${API_BASE}/coursework-ingest-svc/assets`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(assetData),
    })

    if (!response.ok) {
      throw new Error(`Failed to create asset: ${response.statusText}`)
    }

    return response.json()
  }

  async uploadFile(uploadUrl: string, file: File): Promise<void> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(uploadUrl, {
      method: 'PUT',
      body: file,
      headers: {
        'Content-Type': file.type,
      },
    })

    if (!response.ok) {
      throw new Error(`Failed to upload file: ${response.statusText}`)
    }
  }

  async uploadAsset(
    file: File,
    request: CourseworkUploadRequest
  ): Promise<CourseworkUploadResponse> {
    // Step 1: Get upload URL
    const uploadResponse = await fetch(
      `${API_BASE}/coursework-ingest-svc/upload/presigned-url`,
      {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({
          filename: file.name,
          contentType: file.type,
          size: file.size,
        }),
      }
    )

    if (!uploadResponse.ok) {
      throw new Error(`Failed to get upload URL: ${uploadResponse.statusText}`)
    }

    const { uploadUrl, fields, assetId } = await uploadResponse.json()

    // Step 2: Upload file to presigned URL
    const formData = new FormData()
    Object.entries(fields).forEach(([key, value]) => {
      formData.append(key, value as string)
    })
    formData.append('file', file)

    const fileUploadResponse = await fetch(uploadUrl, {
      method: 'POST',
      body: formData,
    })

    if (!fileUploadResponse.ok) {
      throw new Error(`Failed to upload file: ${fileUploadResponse.statusText}`)
    }

    // Step 3: Create asset record
    const assetResponse = await fetch(
      `${API_BASE}/coursework-ingest-svc/assets`,
      {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({
          id: assetId,
          ...request,
        }),
      }
    )

    if (!assetResponse.ok) {
      throw new Error(
        `Failed to create asset record: ${assetResponse.statusText}`
      )
    }

    return assetResponse.json()
  }

  async getOcrPreview(file: File): Promise<OCRPreviewResponse> {
    const response = await fetch(
      `${API_BASE}/coursework-ingest-svc/assets/${assetId}/ocr`,
      {
        method: 'GET',
        headers: this.getAuthHeaders(),
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to get OCR preview: ${response.statusText}`)
    }

    return response.json()
  }

  async attachToLearner(assetId: string, learnerId: string): Promise<void> {
    const response = await fetch(
      `${API_BASE}/coursework-ingest-svc/assets/${assetId}/attach`,
      {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ learnerId }),
      }
    )

    if (!response.ok) {
      throw new Error(
        `Failed to attach asset to learner: ${response.statusText}`
      )
    }
  }

  async deleteAsset(assetId: string): Promise<void> {
    const response = await fetch(
      `${API_BASE}/coursework-ingest-svc/assets/${assetId}`,
      {
        method: 'DELETE',
        headers: this.getAuthHeaders(),
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to delete asset: ${response.statusText}`)
    }
  }

  async updateAsset(
    assetId: string,
    updates: Partial<CourseworkUploadRequest>
  ): Promise<CourseworkAsset> {
    const response = await fetch(
      `${API_BASE}/coursework-ingest-svc/assets/${assetId}`,
      {
        method: 'PATCH',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(updates),
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to update asset: ${response.statusText}`)
    }

    return response.json()
  }

  async attachToLearner(assetId: string, learnerId: string): Promise<void> {
    const response = await fetch(
      `${API_BASE}/coursework-ingest-svc/assets/${assetId}/attach`,
      {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ learnerId }),
      }
    )

    if (!response.ok) {
      throw new Error(
        `Failed to attach asset to learner: ${response.statusText}`
      )
    }
  }

  async detachFromLearner(assetId: string, learnerId: string): Promise<void> {
    const response = await fetch(
      `${API_BASE}/coursework-ingest-svc/assets/${assetId}/detach`,
      {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ learnerId }),
      }
    )

    if (!response.ok) {
      throw new Error(
        `Failed to detach asset from learner: ${response.statusText}`
      )
    }
  }
}

export const courseworkClient = new CourseworkClient()
export default courseworkClient
