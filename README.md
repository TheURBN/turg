<p align="center">
	<img src="https://raw.githubusercontent.com/theurbn/turg/master/assets/urbn_logo.png" alt="allexx was here"/>
</p>

turg
======
🙈 _The most famous The URBN Game backend service. Brain and heart in one bottle._


## Embrace local heroku development

```
brew install heroku
heroku login
heroku git:remote -a turg-svc
heroku config:get MONGODB_URI -s >> .env
heroku local
```#