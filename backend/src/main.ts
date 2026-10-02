import { Logger, ValidationPipe } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { NestFactory } from '@nestjs/core';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { AppModule } from './app.module';
import { AllExceptionsFilter } from './common/filters/all-exceptions.filter';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.setGlobalPrefix('api');
  app.enableCors();
  app.useGlobalPipes(new ValidationPipe({ whitelist: true, transform: true, forbidNonWhitelisted: true }));
  app.useGlobalFilters(new AllExceptionsFilter());
  app.enableShutdownHooks();

  const doc = new DocumentBuilder()
    .setTitle('HomePedia API')
    .setDescription('Collecte, normalisation et consultation des données publiques sur le logement en France')
    .setVersion('0.1.0')
    .build();
  SwaggerModule.setup('api/docs', app, SwaggerModule.createDocument(app, doc));

  const port = app.get(ConfigService).get<number>('port', 3000);
  await app.listen(port);
  Logger.log(`API prête sur http://localhost:${port}/api (Swagger : /api/docs)`, 'Bootstrap');
}
bootstrap();
