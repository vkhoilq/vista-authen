import { useState, useCallback, useRef, useEffect } from "react";
import Webcam from "react-webcam";
import jsQR from "jsqr";

interface QRScannerProps {
  onScan: (qrPayload: string) => void;
  isScanning: boolean;
}

export default function QRScanner({ onScan, isScanning }: QRScannerProps) {
  const webcamRef = useRef<Webcam>(null);
  const [cameraReady, setCameraReady] = useState(false);

  const capture = useCallback(() => {
    if (!cameraReady) return;

    const imageSrc = webcamRef.current?.getScreenshot();
    if (!imageSrc) return;

    const canvas = document.createElement("canvas");
    const img = new Image();
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.drawImage(img, 0, 0);
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const code = jsQR(imageData.data, imageData.width, imageData.height);
      if (code) {
        onScan(code.data);
      }
    };
    img.src = imageSrc;
  }, [cameraReady, onScan]);

  // Poll the camera every 500ms for QR codes
  useEffect(() => {
    if (!isScanning || !cameraReady) return;
    const interval = setInterval(capture, 500);
    return () => clearInterval(interval);
  }, [isScanning, cameraReady, capture]);

  return (
    <div style={{ position: "relative", width: "100%", maxWidth: 400, margin: "0 auto" }}>
      <Webcam
        ref={webcamRef}
        audio={false}
        screenshotFormat="image/png"
        videoConstraints={{
          facingMode: "environment",
          width: 400,
          height: 400,
        }}
        onUserMedia={() => setCameraReady(true)}
        onUserMediaError={() => setCameraReady(false)}
        style={{ width: "100%", borderRadius: 8 }}
      />
      {!cameraReady && (
        <p style={{ textAlign: "center", color: "#888" }}>
          Camera not available. Grant permission or use manual paste below.
        </p>
      )}
    </div>
  );
}