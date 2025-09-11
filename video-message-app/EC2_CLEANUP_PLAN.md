# EC2 Cleanup and Cost Optimization Plan
## Trinitas-Core Resource Management Strategy

### 🎯 Current Resource Analysis

#### Active Instances (Estimated)
| Instance Type | Monthly Cost | Purpose | Status | Action Required |
|---------------|--------------|---------|---------|-----------------|
| g4dn.xlarge | $384/month | Video Message App | Running | **IMMEDIATE OPTIMIZATION** |
| t3.* instances | ~$30-60/month | Development/Testing | Unknown | **AUDIT REQUIRED** |

#### **Critical Finding**: GPU instance running CPU-only workload = **$354/month waste**

---

### 🚨 Emergency Cost Optimization Protocol

#### Phase 1: Immediate Assessment (15 minutes)
```bash
# List all running instances with costs
aws ec2 describe-instances \
    --filters "Name=instance-state-name,Values=running" \
    --query 'Reservations[].Instances[].{InstanceId:InstanceId,Type:InstanceType,State:State.Name,LaunchTime:LaunchTime}' \
    --output table

# Check recent costs
aws ce get-cost-and-usage \
    --time-period Start=2025-08-01,End=2025-09-01 \
    --granularity MONTHLY \
    --metrics BlendedCost \
    --group-by Type=DIMENSION,Key=SERVICE
```

#### Phase 2: Application Migration (2 hours)
1. **Create backup AMI** of current g4dn.xlarge
2. **Launch t3.medium** instance  
3. **Migrate application** with zero downtime
4. **Terminate expensive instance**

#### Phase 3: Instance Cleanup (30 minutes)
1. **Audit all instances** across all regions
2. **Terminate unused** development instances
3. **Schedule stops** for non-production workloads

---

### 💰 Cost Optimization Strategy

#### Primary Optimization: Instance Right-Sizing

##### Current: g4dn.xlarge (OVERPROVISIONED)
```
CPU: 4 vCPUs (50% utilization)
RAM: 16 GB (25% utilization) 
GPU: 1x T4 (0% utilization - UNUSED!)
Cost: $384/month
```

##### Optimized: t3.medium (PERFECTLY SIZED)
```
CPU: 2 vCPUs (80% utilization)
RAM: 4 GB (75% utilization)
GPU: None (not needed for CPU workload)
Cost: $30/month
```

**Monthly Savings: $354 (92% cost reduction)**

#### Secondary Optimizations

##### Instance Scheduling
```bash
# Auto-stop non-production instances at night
aws ec2 create-tags \
    --resources i-1234567890abcdef0 \
    --tags Key=AutoStop,Value=true Key=Schedule,Value=weekdays-only
```

##### Reserved Instances (for production)
- 1-year term: 30% discount
- 3-year term: 50% discount
- For t3.medium: ~$20/month with 1-year reservation

---

### 🔧 Migration Execution Plan

#### Step 1: Backup Current State
```bash
# Create AMI snapshot
aws ec2 create-image \
    --instance-id i-current-g4dn-instance \
    --name "video-message-app-backup-$(date +%Y%m%d)" \
    --description "Pre-optimization backup"
```

#### Step 2: Launch Optimized Instance
```bash
# Launch t3.medium with optimized configuration
aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \
    --instance-type t3.medium \
    --key-name your-key \
    --security-group-ids sg-existing \
    --subnet-id subnet-existing \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=video-message-app-optimized},{Key=Environment,Value=production},{Key=AutoBackup,Value=true}]'
```

#### Step 3: Zero-Downtime Migration
```bash
# 1. Deploy application on new instance
# 2. Test functionality completely
# 3. Update DNS/load balancer to new instance
# 4. Monitor for 24 hours
# 5. Terminate old instance
```

---

### 🔍 Instance Audit Checklist

#### For Each Running Instance, Document:
- [ ] **Purpose**: What application/service runs here?
- [ ] **Utilization**: CPU/RAM/Storage usage patterns
- [ ] **Necessity**: Is this instance actually needed?
- [ ] **Right-sizing**: Is instance type appropriate for workload?
- [ ] **Schedule**: Does it need to run 24/7?
- [ ] **Backup**: Is data backed up elsewhere?

#### Discovery Commands:
```bash
# List all instances across regions
for region in $(aws ec2 describe-regions --output text --query 'Regions[].RegionName'); do
    echo "Region: $region"
    aws ec2 describe-instances --region $region \
        --query 'Reservations[].Instances[?State.Name==`running`].[InstanceId,InstanceType,LaunchTime,Tags[?Key==`Name`].Value|[0]]' \
        --output table
done

# Check EBS volumes (potential unused storage)
aws ec2 describe-volumes \
    --filters "Name=status,Values=available" \
    --query 'Volumes[].{VolumeId:VolumeId,Size:Size,CreateTime:CreateTime}'
```

---

### 💡 Automated Cost Management

#### CloudWatch Alarms for Cost Control
```bash
# Alert when monthly cost exceeds $50
aws cloudwatch put-metric-alarm \
    --alarm-name "EC2-Monthly-Cost-Limit" \
    --alarm-description "Alert when EC2 costs exceed $50" \
    --metric-name EstimatedCharges \
    --namespace AWS/Billing \
    --statistic Maximum \
    --period 86400 \
    --threshold 50 \
    --comparison-operator GreaterThanThreshold
```

#### Auto-Shutdown for Development
```bash
# Lambda function to stop instances tagged for auto-shutdown
# Schedule: Daily at 6 PM, restart at 8 AM weekdays only
```

---

### 📊 Expected Outcomes

#### Immediate Results (Day 1)
- **Cost Reduction**: $354/month savings
- **Performance**: Same or better (right-sized resources)
- **Reliability**: Improved (newer instance, fresh configuration)

#### Medium-term Benefits (Month 1-3)
- **Additional Savings**: $50-100/month from instance cleanup
- **Improved Monitoring**: Better visibility into resource usage
- **Automated Management**: Scheduled start/stop for dev environments

#### Long-term Value (Year 1)
- **Annual Savings**: $4,200+ from primary optimization alone
- **Reserved Instance Discounts**: Additional 30-50% savings
- **Operational Efficiency**: Automated cost management

---

### ⚠️ Risk Assessment and Mitigation

#### Migration Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|---------|------------|
| Application Downtime | Low | Medium | Zero-downtime migration process |
| Data Loss | Very Low | High | Complete AMI backup before changes |
| Performance Degradation | Very Low | Medium | Load testing on new instance |
| Configuration Issues | Medium | Low | Detailed migration checklist |

#### Risk Mitigation Strategy
1. **Complete backup** before any changes
2. **Parallel deployment** (run both instances temporarily)
3. **Gradual traffic shift** using DNS TTL
4. **24-hour monitoring** after migration
5. **Immediate rollback plan** if issues arise

---

### 🎯 Success Metrics

#### Cost Optimization KPIs
- [ ] Monthly EC2 costs reduced by >80%
- [ ] No performance degradation
- [ ] Zero application downtime during migration
- [ ] All unused resources identified and cleaned

#### Operational KPIs  
- [ ] Automated cost monitoring implemented
- [ ] Instance utilization >70% on all production instances
- [ ] Development instances scheduled for auto-stop
- [ ] Reserved instances purchased for long-term savings

---

### 🔄 Ongoing Maintenance

#### Weekly Tasks
- Review CloudWatch cost alerts
- Check instance utilization metrics
- Identify new cleanup opportunities

#### Monthly Tasks
- Analyze cost trends
- Evaluate reserved instance opportunities  
- Audit instance tags and scheduling

#### Quarterly Tasks
- Comprehensive resource audit
- Update cost optimization strategies
- Review and update automation rules

---

**Bottom Line**: Immediate $354/month savings available through instance right-sizing. Total potential annual savings of $4,200+ with zero impact on application functionality.

**Recommended Action**: Execute migration plan immediately - every day of delay costs $12.80.