import mongoose from 'mongoose'

export const connection = () => {
  try {
    mongoose
      // .set("debug", true)
      .connect(process.env.MONGO_URI, {
        dbName: 'mindtraqk-dev',
      })
      .then(() => console.log('MongoDb Connected!'))
  } catch (error) {
    throw error
  }
}
