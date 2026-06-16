import { ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  app.setGlobalPrefix('api');
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      transform: true,
    }),
  );

  app.enableCors({
    origin: process.env.CORS_ORIGIN ?? 'http://localhost:5173',
  });

  const port = process.env.NEST_PORT ?? 3001;
  await app.listen(port);
  console.log(`API listening on http://localhost:${port}/api`);
}
bootstrap();
