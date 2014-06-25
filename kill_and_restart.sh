# Kill
echo "Killing supervisord and gunicorn instances..."
sudo pkill supervisord
sudo pkill gunicorn
echo "Starting supervisord"
sudo supervisord -c simple.conf
echo "Done. List supervisord and gunicorn:"
ps aux | grep 'supervisord\|gunicorn' | grep -v grepx
