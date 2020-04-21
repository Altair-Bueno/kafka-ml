
from rest_framework import serializers
from automl.models import MLModel, Configuration, Deployment, TraningResult, Datasource

class MLModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MLModel
        fields = ['id', 'code', 'name', 'description', 'imports']

class SimpleModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MLModel
        fields = ['id', 'name']

class SimpleDeploymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deployment
        fields = ['id','time', 'status']
        
class ConfigurationSerializer(serializers.ModelSerializer):
    ml_models = SimpleModelSerializer(many=True, read_only=True)
    deployments = SimpleDeploymentSerializer(many=True, read_only=True)
    class Meta:
        model = Configuration
        fields = ['id', 'name', 'description', 'ml_models', 'deployments']
    

    def update(self, instance, validated_data):
        ml_models = self.initial_data.get("ml_models") if "ml_models" in self.initial_data else []

        for (key, value) in validated_data.items():
            setattr(instance, key, value)

        for existing_model in instance.ml_models.all():
            """Delete existing relations"""
            instance.ml_models.remove(existing_model)
        
        for model in ml_models:
            """Add new relations"""
            instance.ml_models.add(MLModel.objects.get(pk=model['id']))
        
        return instance

    def create(self, validated_data):
        ml_models = self.initial_data.get("ml_models") if "ml_models" in self.initial_data else []
        configuration = Configuration.objects.create(**validated_data)
        for model in ml_models:
            configuration.ml_models.add(MLModel.objects.get(pk=model))
        return configuration

class SimpleConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Configuration
        fields = ['id', 'name']

class SimpleTrainingResultSerializer(serializers.ModelSerializer):    
    model = SimpleModelSerializer()

    class Meta:
        model = TraningResult
        fields = ['id', 'status', 'model', 'status_changed']

class DeployDeploymentSerializer(serializers.ModelSerializer):
    configuration = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = Deployment
        fields = ['batch', 'kwargs_fit', 'configuration']
    
    def validate_batch(self, value):
        """Checks that batch size is greater than 0"""
        
        if value <= 0:
            raise serializers.ValidationError("Batch has to be greater than 0")
        return value
    
    def validate_kwargs_fit(self, value):
        """Checks that arguments for training have the expected format"""
        import re
        if not bool(re.match('^[a-z0-9-_]*[ ]*=[ ]*[a-z0-9-_][ ]*(,[ ]*[a-z0-9-_]*[ ]*=[ ]*[a-z0-9-_]*[ ]*)*$', value)):
            raise serializers.ValidationError("Arguments for training do not have the expected format")
        return value

    def create(self, validated_data):
        """Creates a new deployment, associated it with the configuration and creates related results"""

        configuration_id = self.initial_data.get("configuration") if "configuration" in self.initial_data else ''
        configuration = Configuration.objects.get(pk=configuration_id)
        deployment = Deployment.objects.create(configuration=configuration, **validated_data)
        for model in configuration.ml_models.all():
                    TraningResult.objects.create(model=model, deployment=deployment)
        return deployment

class DeploymentSerializer(serializers.ModelSerializer):
    configuration = SimpleConfigurationSerializer()
    results = SimpleTrainingResultSerializer(many=True, read_only=True)

    class Meta:
        model = Deployment
        fields = ['id', 'configuration', 'results', 'status', 'status_changed', 'batch', 'kwargs_fit', 'time']

class RoundingDecimalField(serializers.DecimalField):
    """Used to automatically round decimals to the model's accepted value."""

    def validate_precision(self, value):
        return value

class SimpleResultSerializer(serializers.ModelSerializer):
    val_loss = RoundingDecimalField(max_digits=15, decimal_places=10)
    val_acc = RoundingDecimalField(max_digits=15, decimal_places=10)
    class Meta:
        model = TraningResult
        fields = ['id', 'train_loss_hist', 'train_acc_hist', 'val_loss', 'val_acc']

class TrainingResultSerializer(serializers.ModelSerializer):
    deployment = SimpleDeploymentSerializer()
    model = SimpleModelSerializer()
    
    class Meta:
        model = TraningResult
        fields = ['id', 'status', 'status_changed', 'deployment', 
                'model', 'train_loss_hist','train_acc_hist','val_loss','val_acc']

class DatasourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Datasource
        fields = ['input_format', 'deployment', 'configuration',
        'description', 'topic', 'validation_rate', 'total_msg', 'time']