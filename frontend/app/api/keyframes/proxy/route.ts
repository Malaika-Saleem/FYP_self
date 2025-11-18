import { NextRequest, NextResponse } from 'next/server';

/**
 * Proxy endpoint for keyframe images from MinIO
 * Handles presigned URLs that point to localhost:9000
 * Usage: /api/keyframes/proxy?url=<encoded_presigned_url>
 */
export async function GET(request: NextRequest) {
  try {
    // Extract the MinIO presigned URL from query params
    const presignedUrl = request.nextUrl.searchParams.get('url');
    
    if (!presignedUrl) {
      return NextResponse.json(
        { error: 'Missing presigned URL parameter' },
        { status: 400 }
      );
    }

    console.log('Proxying keyframe request:', presignedUrl.substring(0, 100) + '...');

    const response = await fetch(presignedUrl, {
      method: 'GET',
      headers: {
        'Accept': 'image/jpeg,image/jpg,image/*',
      },
    });

    if (!response.ok) {
      console.error('MinIO returned error:', response.status, response.statusText);
      return NextResponse.json(
        { error: `MinIO returned ${response.status}: ${response.statusText}` },
        { status: response.status }
      );
    }

    // Get the image data
    const imageData = await response.arrayBuffer();
    const contentType = response.headers.get('content-type') || 'image/jpeg';

    console.log('Streaming keyframe image:', {
      contentType,
      dataSize: imageData.byteLength
    });

    // Return the image with proper headers
    return new NextResponse(imageData, {
      status: 200,
      headers: {
        'Content-Type': contentType,
        'Content-Length': imageData.byteLength.toString(),
        'Cache-Control': 'public, max-age=3600',
      },
    });
  } catch (error) {
    console.error('Error proxying keyframe image:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to fetch keyframe image' },
      { status: 500 }
    );
  }
}
