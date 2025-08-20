#!/bin/bash

# GPUスポットインスタンス起動スクリプト
# g4dn.xlarge with Deep Learning AMI

echo "=== GPU Spot Instance Launch Script ==="
echo "Instance Type: g4dn.xlarge"
echo "Purpose: OpenVoice V2 GPU Processing"
echo ""

# 設定
PROFILE="video-app"
REGION="ap-northeast-1"
INSTANCE_TYPE="g4dn.xlarge"
MAX_PRICE="0.35"
KEY_NAME="video-app-key"
AMI_ID="ami-012750db2fd2a07bd"  # Deep Learning Base GPU AMI (Ubuntu 22.04) - Tokyo Region

# セキュリティグループの作成または取得
echo "Checking security group..."
SG_ID=$(aws ec2 describe-security-groups \
    --profile $PROFILE \
    --filters "Name=group-name,Values=openvoice-gpu-sg" \
    --query "SecurityGroups[0].GroupId" \
    --output text 2>/dev/null)

if [ "$SG_ID" == "None" ] || [ -z "$SG_ID" ]; then
    echo "Creating security group..."
    VPC_ID=$(aws ec2 describe-vpcs \
        --profile $PROFILE \
        --filters "Name=is-default,Values=true" \
        --query "Vpcs[0].VpcId" \
        --output text)
    
    SG_ID=$(aws ec2 create-security-group \
        --profile $PROFILE \
        --group-name openvoice-gpu-sg \
        --description "Security group for OpenVoice GPU instance" \
        --vpc-id $VPC_ID \
        --query "GroupId" \
        --output text)
    
    # SSH access
    aws ec2 authorize-security-group-ingress \
        --profile $PROFILE \
        --group-id $SG_ID \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0
    
    # OpenVoice service port
    aws ec2 authorize-security-group-ingress \
        --profile $PROFILE \
        --group-id $SG_ID \
        --protocol tcp \
        --port 8001 \
        --cidr 0.0.0.0/0
    
    echo "Security group created: $SG_ID"
else
    echo "Using existing security group: $SG_ID"
fi

# User Dataスクリプト
USER_DATA=$(cat <<'EOF'
#!/bin/bash
apt-get update
apt-get install -y python3-pip git ffmpeg

# NVIDIA Driver check
nvidia-smi

# Conda installation
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
bash miniconda.sh -b -p /opt/conda
rm miniconda.sh
export PATH="/opt/conda/bin:$PATH"

# OpenVoice V2 setup
cd /home/ubuntu
git clone https://github.com/myshell-ai/OpenVoice.git
cd OpenVoice

# Create conda environment
/opt/conda/bin/conda create -n openvoice_v2 python=3.11 -y
source /opt/conda/bin/activate openvoice_v2

# Install dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install -e .
pip install fastapi uvicorn python-multipart aiofiles

# Create OpenVoice service script
cat > /home/ubuntu/openvoice_service.py << 'SCRIPT'
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import tempfile
import uuid
from pathlib import Path
import torch
from openvoice import se_extractor
from openvoice.api import ToneColorConverter

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize models
device = "cuda" if torch.cuda.is_available() else "cpu"
ckpt_converter = 'checkpoints_v2/converter'
tone_color_converter = ToneColorConverter(f'{ckpt_converter}/config.json', device=device)
tone_color_converter.load_ckpt(f'{ckpt_converter}/checkpoint.pth')

# Storage directory
STORAGE_DIR = Path("/home/ubuntu/openvoice_storage")
STORAGE_DIR.mkdir(exist_ok=True)

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "openvoice_v2",
        "device": device,
        "cuda_available": torch.cuda.is_available()
    }

@app.post("/extract")
async def extract_features(
    audio_file: UploadFile = File(...),
    profile_id: str = Form(...)
):
    """Extract voice features from audio file"""
    try:
        # Save uploaded file
        temp_path = f"/tmp/{uuid.uuid4()}.wav"
        with open(temp_path, "wb") as f:
            content = await audio_file.read()
            f.write(content)
        
        # Extract features
        target_se, _ = se_extractor.get_se(
            temp_path, 
            tone_color_converter, 
            vad=False
        )
        
        # Save features
        profile_dir = STORAGE_DIR / profile_id
        profile_dir.mkdir(exist_ok=True)
        feature_path = profile_dir / "features.pth"
        torch.save(target_se, feature_path)
        
        os.remove(temp_path)
        
        return {
            "success": True,
            "profile_id": profile_id,
            "feature_path": str(feature_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/synthesize")
async def synthesize_voice(
    text: str = Form(...),
    profile_id: str = Form(...),
    source_audio: UploadFile = File(...)
):
    """Synthesize voice with cloned characteristics"""
    try:
        # Load features
        feature_path = STORAGE_DIR / profile_id / "features.pth"
        if not feature_path.exists():
            raise HTTPException(status_code=404, detail="Profile not found")
        
        target_se = torch.load(feature_path, map_location=device)
        
        # Save source audio
        source_path = f"/tmp/{uuid.uuid4()}.wav"
        with open(source_path, "wb") as f:
            content = await source_audio.read()
            f.write(content)
        
        # Convert voice
        output_path = f"/tmp/{uuid.uuid4()}_output.wav"
        source_se, _ = se_extractor.get_se(
            source_path, 
            tone_color_converter, 
            vad=False
        )
        
        tone_color_converter.convert(
            audio_src_path=source_path,
            src_se=source_se,
            tgt_se=target_se,
            output_path=output_path,
            message=text
        )
        
        # Clean up
        os.remove(source_path)
        
        return FileResponse(
            output_path,
            media_type="audio/wav",
            filename=f"synthesized_{profile_id}.wav"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
SCRIPT

# Create systemd service
cat > /etc/systemd/system/openvoice.service << 'SERVICE'
[Unit]
Description=OpenVoice V2 GPU Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/OpenVoice
Environment="PATH=/opt/conda/envs/openvoice_v2/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/opt/conda/envs/openvoice_v2/bin/python /home/ubuntu/openvoice_service.py
Restart=always

[Install]
WantedBy=multi-user.target
SERVICE

# Download checkpoints
cd /home/ubuntu/OpenVoice
wget https://myshell-public-repo-host.s3.amazonaws.com/openvoice/checkpoints_v2_0417.zip
unzip checkpoints_v2_0417.zip
rm checkpoints_v2_0417.zip

# Set permissions
chown -R ubuntu:ubuntu /home/ubuntu/OpenVoice
chown -R ubuntu:ubuntu /home/ubuntu/openvoice_storage

# Start service
systemctl daemon-reload
systemctl enable openvoice
systemctl start openvoice

echo "OpenVoice V2 GPU Service started on port 8001"
EOF
)

# Base64エンコード
USER_DATA_ENCODED=$(echo "$USER_DATA" | base64 -w 0)

# スポットインスタンスリクエストの作成
echo "Launching spot instance..."
SPOT_REQUEST=$(aws ec2 request-spot-instances \
    --profile $PROFILE \
    --spot-price "$MAX_PRICE" \
    --instance-count 1 \
    --type "persistent" \
    --launch-specification '{
        "ImageId": "'$AMI_ID'",
        "InstanceType": "'$INSTANCE_TYPE'",
        "KeyName": "'$KEY_NAME'",
        "SecurityGroupIds": ["'$SG_ID'"],
        "UserData": "'$USER_DATA_ENCODED'",
        "BlockDeviceMappings": [
            {
                "DeviceName": "/dev/sda1",
                "Ebs": {
                    "VolumeSize": 100,
                    "VolumeType": "gp3",
                    "DeleteOnTermination": true
                }
            }
        ]
    }' \
    --query "SpotInstanceRequests[0].SpotInstanceRequestId" \
    --output text)

echo "Spot request created: $SPOT_REQUEST"
echo "Waiting for instance to launch..."

# インスタンスIDの取得を待つ
for i in {1..30}; do
    INSTANCE_ID=$(aws ec2 describe-spot-instance-requests \
        --profile $PROFILE \
        --spot-instance-request-ids $SPOT_REQUEST \
        --query "SpotInstanceRequests[0].InstanceId" \
        --output text 2>/dev/null)
    
    if [ "$INSTANCE_ID" != "None" ] && [ -n "$INSTANCE_ID" ]; then
        echo "Instance launched: $INSTANCE_ID"
        break
    fi
    echo "Waiting... ($i/30)"
    sleep 10
done

if [ "$INSTANCE_ID" == "None" ] || [ -z "$INSTANCE_ID" ]; then
    echo "Failed to launch instance"
    exit 1
fi

# インスタンスが実行中になるまで待つ
echo "Waiting for instance to be running..."
aws ec2 wait instance-running --profile $PROFILE --instance-ids $INSTANCE_ID

# パブリックIPの取得
PUBLIC_IP=$(aws ec2 describe-instances \
    --profile $PROFILE \
    --instance-ids $INSTANCE_ID \
    --query "Reservations[0].Instances[0].PublicIpAddress" \
    --output text)

echo ""
echo "========================================="
echo "GPU Instance Launched Successfully!"
echo "========================================="
echo "Instance ID: $INSTANCE_ID"
echo "Public IP: $PUBLIC_IP"
echo "Instance Type: $INSTANCE_TYPE"
echo "Spot Request ID: $SPOT_REQUEST"
echo ""
echo "OpenVoice Service will be available at:"
echo "http://$PUBLIC_IP:8001"
echo ""
echo "SSH Access:"
echo "ssh -i ~/.ssh/video-app-key.pem ubuntu@$PUBLIC_IP"
echo ""
echo "Next Steps:"
echo "1. Wait 5-10 minutes for User Data script to complete"
echo "2. Test service: curl http://$PUBLIC_IP:8001/health"
echo "3. Update t3.large backend/.env:"
echo "   OPENVOICE_SERVICE_URL=http://$PUBLIC_IP:8001"
echo "========================================="

# 設定ファイルに保存
cat > ~/gpu_instance_info.txt << EOL
INSTANCE_ID=$INSTANCE_ID
PUBLIC_IP=$PUBLIC_IP
SPOT_REQUEST_ID=$SPOT_REQUEST
OPENVOICE_URL=http://$PUBLIC_IP:8001
EOL

echo "Instance info saved to ~/gpu_instance_info.txt"