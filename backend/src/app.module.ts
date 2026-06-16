import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { join } from 'path';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { BotsModule } from './bots/bots.module';
import { Bot, Candle, News, Signal, Trade } from './entities';
import { GatewayModule } from './gateway/gateway.module';
import { NewsModule } from './news/news.module';
import { PerformanceModule } from './performance/performance.module';
import { RedisModule } from './redis/redis.module';
import { TradesModule } from './trades/trades.module';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: join(__dirname, '..', '..', '.env'),
    }),
    TypeOrmModule.forRootAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (configService: ConfigService) => ({
        type: 'postgres',
        url: configService.get<string>(
          'DATABASE_URL',
          'postgresql://trading:trading@localhost:5432/trading',
        ),
        entities: [Bot, Trade, Signal, News, Candle],
        synchronize: false,
      }),
    }),
    RedisModule,
    BotsModule,
    TradesModule,
    NewsModule,
    PerformanceModule,
    GatewayModule,
  ],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
