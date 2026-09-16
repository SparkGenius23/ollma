
class ModelOutputReadinessIndex(models.Model):
    time = TimescaleDateTimeField(interval="7 days") # The time field
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='User_model_output_readiness_index')
    date = models.DateField()
    ri_base = models.FloatField(null=True, blank=True)
    penalty_factors = models.FloatField(null=True, blank=True)
    ri_final = models.FloatField(null=True, blank=True)
    readiness_score = models.FloatField(null=True, blank=True)
    readiness_zone = models.CharField(max_length=10, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='low')
    penalty_triggers = models.JSONField(null=True, blank=True)
    key_drivers = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=[('calibrating', 'Calibrating'), ('active', 'Active'), ('inactive', 'Inactive')], default='calibrating')
    intel_output=models.JSONField(null=True, blank=True)

    objects = models.Manager()
    timescale = TimescaleManager()
    class Meta:
        db_table = 'ts_model_output_readiness_index'

class ModelOutputRecoveryScore(models.Model):
    time = TimescaleDateTimeField(interval="7 days") # The time field
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='User_model_output_recovery_score')
    date = models.DateField()
    hrv_score = models.FloatField(null=True, blank=True)
    rhr_score = models.FloatField(null=True, blank=True)
    sleep_score = models.FloatField(null=True, blank=True)
    nutrition_ratio = models.FloatField(null=True, blank=True)
    hydration_score = models.FloatField(null=True, blank=True)
    ari_score = models.FloatField(null=True, blank=True)
    spo2_score = models.FloatField(null=True, blank=True)
    stress_score = models.FloatField(null=True, blank=True)
    soreness_score = models.FloatField(null=True, blank=True)
    fatigue_score = models.FloatField(null=True, blank=True)
    recovery_score = models.FloatField(null=True, blank=True)
    penalty_factor = models.FloatField(null=True, blank=True)
    interpretation_band = models.CharField(max_length=20, choices=[('excellent', 'Excellent'), ('moderate', 'Moderate'), ('poor', 'Poor'), ('very_poor', 'Very Poor')], default='poor')
    intel_output=models.JSONField(null=True, blank=True)
    key_drivers = models.JSONField(null=True, blank=True)
    
    objects = models.Manager()
    timescale = TimescaleManager()
    class Meta:
        db_table = 'ts_model_output_recovery_score'

class ModelOutputRiskScore(models.Model):
    time = TimescaleDateTimeField(interval="7 days") # The time field
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='User_model_output_risk_score')
    date = models.DateField()
    injury_risk_prob = models.FloatField(null=True, blank=True)
    risk_band = models.CharField(max_length=20, choices=[('green', 'Green'), ('yellow', 'Yellow'), ('red', 'Red')], default='low')
    key_drivers = models.JSONField(null=True, blank=True)
    model_version = models.CharField(max_length=50)
    risk_zone=models.CharField(max_length=30, null=True, blank=True)
    intel_output=models.JSONField(null=True, blank=True)

    objects = models.Manager()
    timescale = TimescaleManager()
    class Meta:
        db_table = 'ts_model_output_risk_score'


class MOHealthBandDaily(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='User_mo_health_band_daily')
    date = models.DateField()
    readiness_score = models.FloatField()
    recovery_score = models.FloatField()
    injury_risk_score = models.FloatField()
    health_band = models.FloatField()
    band_confidence = models.FloatField()
    model_confidence = models.CharField(max_length=15)
    startup_phase_flag = models.BooleanField(default=False)
    intel_output=models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    key_drivers=models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'model_output_health_band_daily'
