for i in 1 2 3 4 5; do
  gcloud compute ssh toydb-node-$i --zone europe-west3-c --command "sudo systemctl restart toydb"
done
