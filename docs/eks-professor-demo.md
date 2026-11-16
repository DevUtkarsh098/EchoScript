# Temporary AWS EKS professor demo

This demo adds a separate Amazon EKS cluster in `us-west-2` to show Kubernetes running in AWS. The production EchoScript application remains on its existing ECS/Fargate deployment; this demo does not migrate or modify its services or data.

The cluster has one small managed EC2 worker and a two-pod EchoScript-branded web demo. It uses a dedicated eksctl-managed VPC with NAT disabled. The EKS API endpoint is limited to the operator's public IP. The web service is internal to Kubernetes; use `kubectl port-forward` to view it from the laptop. No public load balancer is created.

## Cost and lifecycle

The EKS control plane and worker are billed hourly while the cluster exists. A t3a.medium worker keeps the compute estimate below the earlier t3a.large estimate; EBS storage, public IPv4, data transfer, and other account usage can add charges. These are estimates, not an AWS spending cap. Keep the demo only as long as needed and delete it after the presentation.

## Create the cluster

1. Configure AWS SSO and verify that the active profile is the intended account.
2. In `infrastructure/kubernetes/eks-demo/cluster.yaml`, replace `REPLACE_WITH_YOUR_PUBLIC_IP/32` with the operator's current public IPv4 address in CIDR form. This limits access to the Kubernetes API.
3. Create the AWS cluster and managed worker:

   ```sh
   eksctl create cluster --config-file infrastructure/kubernetes/eks-demo/cluster.yaml
   ```

4. Configure kubectl for the demo cluster:

   ```sh
   aws eks update-kubeconfig --name echoscript-professor-demo --region us-west-2 --profile echoscript-deploy
   ```

5. Apply the demo workload and wait for it to become ready:

   ```sh
   kubectl apply -f infrastructure/kubernetes/eks-demo/workload.yaml
   kubectl rollout status deployment/echoscript-demo -n echoscript-demo
   ```

## Show the demo

Show the AWS EKS cluster in the AWS console, then use these commands to display the Kubernetes worker, pods, deployment, and Service:

```sh
kubectl get nodes -o wide
kubectl get deployment,pods,svc -n echoscript-demo -o wide
```

To view the page, leave this command running in a terminal and open `http://localhost:18080`:

```sh
kubectl port-forward --address 127.0.0.1 service/echoscript-demo 18080:80 -n echoscript-demo
```

The page is served by pods running in AWS. Port forwarding only carries browser traffic from the laptop to the AWS-hosted Service.

## Delete after the presentation

Delete the Kubernetes resources and the EKS cluster, managed worker, and demo VPC:

```sh
kubectl delete -f infrastructure/kubernetes/eks-demo/workload.yaml
eksctl delete cluster --config-file infrastructure/kubernetes/eks-demo/cluster.yaml
```

Wait for eksctl to finish deleting both CloudFormation stacks. Check the CloudFormation console for any failed cleanup before considering the demo removed. Deletion does not remove unrelated project ECS resources, data, or repositories.
