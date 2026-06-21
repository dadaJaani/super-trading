import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Candle } from '../entities/candle.entity';
import { CandlesController } from './candles.controller';
import { CandlesService } from './candles.service';

@Module({
  imports: [TypeOrmModule.forFeature([Candle])],
  controllers: [CandlesController],
  providers: [CandlesService],
})
export class CandlesModule {}
